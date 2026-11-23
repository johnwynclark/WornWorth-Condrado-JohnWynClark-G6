from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from listings.models import Listing

from . import services
from .forms import CheckoutForm
from .models import Address, Order

Role = User.Role


def _orders_for(user):
    """Orders this user is allowed to see: buyers their own, sellers those containing
    their listings, admins all."""
    qs = Order.objects.select_related("buyer", "address").prefetch_related("items__listing__images")
    if user.role == Role.BUYER:
        return qs.filter(buyer=user)
    if user.role == Role.SELLER:
        return qs.filter(items__listing__seller=user).distinct()
    return qs


def _get_order(user, pk):
    return get_object_or_404(_orders_for(user), pk=pk)


@role_required(Role.BUYER)
def checkout(request, listing_pk):
    listing = get_object_or_404(Listing.objects.select_related("category", "seller").prefetch_related("images"), pk=listing_pk)
    if not listing.is_available or listing.seller_id == request.user.pk:
        messages.error(request, "That item isn't available to buy.")
        return redirect("listings:browse")
    last_address = Address.objects.filter(user=request.user).order_by("-pk").first()
    form = CheckoutForm(
        request.POST or None, user=request.user, listing=listing,
        initial={"quantity": 1, "address": last_address, "recipient_name": request.user.full_name, "phone": request.user.phone},
    )
    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():  # a new address is rolled back if the order fails
                    order = services.place_order(request.user, listing.pk, form.cleaned_data["quantity"], form.get_address())
            except services.OrderError as exc:
                messages.error(request, str(exc))
                return redirect("listings:detail", pk=listing.pk)
            messages.success(request, f"Order {order.order_reference} placed. The seller will confirm it soon.")
            return redirect("orders:detail", pk=order.pk)
        messages.error(request, "Your order wasn't placed. Fix the highlighted fields.")
    return render(request, "orders/checkout.html", {"form": form, "listing": listing, "delivery_fee": settings.DELIVERY_FEE})


@login_required
def order_list(request):
    qs = _orders_for(request.user)
    current = request.GET.get("status", "")
    if current in Order.Status.values:
        qs = qs.filter(order_status=current)
    q = request.GET.get("q", "").strip()
    if q and request.user.role == Role.ADMIN:
        qs = qs.filter(Q(order_reference__icontains=q) | Q(buyer__email__icontains=q) | Q(buyer__full_name__icontains=q))
    page = Paginator(qs.order_by("-ordered_at"), 15).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "orders/list.html", {
        "page": page, "current": current, "q": q, "statuses": Order.Status.choices, "querystring": params.urlencode(),
    })


@login_required
def order_detail(request, pk):
    order = _get_order(request.user, pk)
    role = request.user.role
    return render(request, "orders/detail.html", {
        "order": order,
        "timeline": [(value, label) for value, label in Order.Status.choices if value in Order.TIMELINE],
        "is_buyer": role == Role.BUYER,
        "is_seller": role == Role.SELLER,
        "can_cancel": role in (Role.BUYER, Role.SELLER) and order.can_cancel,
        "can_advance": role == Role.SELLER and order.seller_next is not None,
        "can_receive": role == Role.BUYER and order.order_status == Order.Status.SHIPPED,
    })


def _run(request, pk, action, success):
    order = _get_order(request.user, pk)
    try:
        action(order.pk)
        messages.success(request, success)
    except services.OrderError as exc:
        messages.error(request, str(exc))
    return redirect("orders:detail", pk=order.pk)


@require_POST
@role_required(Role.BUYER, Role.SELLER)
def order_cancel(request, pk):
    return _run(request, pk, services.cancel_order, "Order cancelled and the item was returned to stock.")


@require_POST
@role_required(Role.SELLER)
def order_advance(request, pk):
    return _run(request, pk, services.advance_order, "Order status updated.")


@require_POST
@role_required(Role.BUYER)
def order_received(request, pk):
    return _run(request, pk, services.complete_order, "Thanks. The order is now completed.")
