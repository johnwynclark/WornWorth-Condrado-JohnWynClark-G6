from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import LoginForm, ProfileForm, RegistrationForm
from .models import User
from listings.models import Listing
from orders.models import Order

DASHBOARD_BY_ROLE = {
    User.Role.BUYER: "accounts:buyer_dashboard",
    User.Role.SELLER: "accounts:seller_dashboard",
    User.Role.ADMIN: "accounts:admin_dashboard",
}


def home(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return render(request, "home.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. Log in to start using WornWorth.")
            return redirect("accounts:login")
        messages.error(request, "We couldn't create your account. Fix the highlighted fields and try again.")
    return render(request, "accounts/register.html", {"form": form})


class WornWorthLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().full_name.split()[0]}.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Login failed. See the message below.")
        return super().form_invalid(form)


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You've been logged out.")
    return redirect("accounts:login")


@login_required
def dashboard(request):
    """Send each user to the dashboard for their role."""
    return redirect(DASHBOARD_BY_ROLE[request.user.role])


@role_required(User.Role.BUYER)
def buyer_dashboard(request):
    orders = Order.objects.filter(buyer=request.user)
    context = {
        "active_orders": orders.exclude(order_status__in=[Order.Status.COMPLETED, Order.Status.CANCELLED]).count(),
        "completed_orders": orders.filter(order_status=Order.Status.COMPLETED).count(),
        "recent_orders": orders.prefetch_related("items__listing")[:5],
        "available_count": Listing.objects.filter(listing_status=Listing.Status.ACTIVE, quantity__gt=0).count(),
    }
    return render(request, "dashboards/buyer.html", context)


@role_required(User.Role.SELLER)
def seller_dashboard(request):
    mine = Listing.objects.filter(seller=request.user)
    orders = Order.objects.filter(items__listing__seller=request.user).distinct()
    context = {
        "live_count": mine.filter(listing_status=Listing.Status.ACTIVE).count(),
        "draft_count": mine.filter(listing_status=Listing.Status.DRAFT).count(),
        "pending_orders": orders.filter(order_status=Order.Status.PENDING).count(),
        "to_ship_orders": orders.filter(order_status__in=[Order.Status.CONFIRMED, Order.Status.PROCESSING]).count(),
        "recent_orders": orders.prefetch_related("items__listing").order_by("-ordered_at")[:5],
    }
    return render(request, "dashboards/seller.html", context)


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "buyer_count": User.objects.filter(role=User.Role.BUYER).count(),
        "seller_count": User.objects.filter(role=User.Role.SELLER).count(),
        "suspended_count": User.objects.exclude(account_status=User.Status.ACTIVE).count(),
        "recent_users": User.objects.order_by("-created_at")[:8],
        "listing_count": Listing.objects.count(),
        "live_listing_count": Listing.objects.filter(listing_status=Listing.Status.ACTIVE).count(),
        "order_count": Order.objects.count(),
        "pending_order_count": Order.objects.filter(order_status=Order.Status.PENDING).count(),
    }
    return render(request, "dashboards/admin.html", context)


@login_required
def profile(request):
    # Always the logged-in user; there is no user id in the URL.
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
        messages.error(request, "Your changes weren't saved. Fix the highlighted fields.")
    return render(request, "accounts/profile_edit.html", {"form": form})
