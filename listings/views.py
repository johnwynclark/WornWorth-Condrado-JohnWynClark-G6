from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms import ListingCreateForm, ListingFilterForm, ListingForm, ListingImageForm
from .models import Listing, ListingImage

MAX_IMAGES = 6
SORTS = {"newest": "-created_at", "price_low": "price", "price_high": "-price"}
Status = Listing.Status


def _next_or(request, default):
    """Redirect target from a POSTed 'next', only if it stays on this site."""
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(default)


# ---------- Buyer: browse and view ----------
@role_required(User.Role.BUYER)
def browse(request):
    form = ListingFilterForm(request.GET)
    qs = (
        Listing.objects.filter(listing_status=Status.ACTIVE, quantity__gt=0)
        .select_related("category", "seller")
        .prefetch_related("images")
    )
    sort = "newest"
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            qs = qs.filter(Q(title__icontains=d["q"]) | Q(description__icontains=d["q"]))
        if d["category"]:
            qs = qs.filter(category=d["category"])
        if d["size"]:
            qs = qs.filter(size__iexact=d["size"].strip())
        if d["condition"]:
            qs = qs.filter(condition=d["condition"])
        if d["min_price"] is not None:
            qs = qs.filter(price__gte=d["min_price"])
        if d["max_price"] is not None:
            qs = qs.filter(price__lte=d["max_price"])
        sort = d["sort"] or "newest"
    page = Paginator(qs.order_by(SORTS[sort]), 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "listings/browse.html", {"form": form, "page": page, "querystring": params.urlencode()})


@login_required
def listing_detail(request, pk):
    listing = get_object_or_404(Listing.objects.select_related("category", "seller").prefetch_related("images"), pk=pk)
    role = request.user.role
    if role == User.Role.BUYER and listing.listing_status != Status.ACTIVE:
        raise Http404
    if role == User.Role.SELLER and listing.seller_id != request.user.pk:
        raise Http404
    context = {"listing": listing, "can_buy": role == User.Role.BUYER and listing.is_available}
    return render(request, "listings/detail.html", context)


# ---------- Seller: manage own listings (CRUD) ----------
@role_required(User.Role.SELLER)
def my_listings(request):
    mine = Listing.objects.filter(seller=request.user)
    counts = {row["listing_status"]: row["n"] for row in mine.values("listing_status").annotate(n=Count("pk"))}
    current = request.GET.get("status", "")
    qs = mine.select_related("category").prefetch_related("images")
    if current in Status.values:
        qs = qs.filter(listing_status=current)
    return render(request, "listings/seller_list.html", {
        "listings": qs, "current": current, "total": sum(counts.values()),
        "status_tabs": [(v, label, counts.get(v, 0)) for v, label in Status.choices],
    })


@role_required(User.Role.SELLER)
def listing_create(request):
    form = ListingCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            publish = request.POST.get("action") == "publish"
            image = form.cleaned_data.get("image")
            if publish and not image:
                form.add_error("image", "Add a main photo before publishing.")  # BR-07
            else:
                with transaction.atomic():
                    listing = form.save(commit=False)
                    listing.seller = request.user  # BR-06
                    listing.listing_status = Status.ACTIVE if publish else Status.DRAFT
                    listing.save()
                    if image:
                        ListingImage.objects.create(listing=listing, uploaded_by=request.user, image=image, is_primary=True)
                messages.success(request, "Listing published." if publish else "Draft saved. Add photos and publish when ready.")
                return redirect("listings:my_listings")
        messages.error(request, "The listing wasn't saved. Fix the highlighted fields.")
    return render(request, "listings/form.html", {"form": form, "listing": None})


def _own_listing(request, pk):
    return get_object_or_404(Listing, pk=pk, seller=request.user)  # BR-08


@role_required(User.Role.SELLER)
def listing_edit(request, pk):
    listing = _own_listing(request, pk)
    if listing.listing_status == Status.REMOVED:
        messages.error(request, "An administrator removed this listing, so it can't be edited.")
        return redirect("listings:my_listings")
    form = ListingForm(request.POST or None, instance=listing)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Listing updated.")
            return redirect("listings:edit", pk=listing.pk)
        messages.error(request, "Your changes weren't saved. Fix the highlighted fields.")
    images = listing.images.all()
    return render(request, "listings/form.html", {
        "form": form, "listing": listing, "images": images,
        "image_form": ListingImageForm(), "can_add_image": images.count() < MAX_IMAGES, "max_images": MAX_IMAGES,
    })


@require_POST
@role_required(User.Role.SELLER)
def listing_status(request, pk):
    listing = _own_listing(request, pk)
    target = request.POST.get("target")
    if listing.listing_status == Status.REMOVED:
        messages.error(request, "An administrator removed this listing.")
    elif target == Status.ACTIVE:
        if not listing.images.exists():
            messages.error(request, "Add at least one photo before publishing.")  # BR-07
        else:
            listing.listing_status = Status.ACTIVE
            listing.save(update_fields=["listing_status", "updated_at"])
            messages.success(request, "Listing is now live.")
    elif target == Status.INACTIVE:
        listing.listing_status = Status.INACTIVE
        listing.save(update_fields=["listing_status", "updated_at"])
        messages.success(request, "Listing deactivated. Buyers can no longer see or buy it.")  # BR-12
    return _next_or(request, "listings:my_listings")


@require_POST
@role_required(User.Role.SELLER)
def listing_delete(request, pk):
    listing = _own_listing(request, pk)
    if listing.order_items.exists():
        # BR-30: keep order history; deactivate instead of deleting
        listing.listing_status = Status.INACTIVE
        listing.save(update_fields=["listing_status", "updated_at"])
        messages.info(request, "This item has past orders, so it was deactivated instead of deleted.")
    else:
        for image in listing.images.all():
            image.image.delete(save=False)
        listing.delete()
        messages.success(request, "Listing deleted.")
    return redirect("listings:my_listings")


@require_POST
@role_required(User.Role.SELLER)
def image_add(request, pk):
    listing = _own_listing(request, pk)
    form = ListingImageForm(request.POST, request.FILES)
    if listing.images.count() >= MAX_IMAGES:
        messages.error(request, f"A listing can have at most {MAX_IMAGES} photos.")
    elif form.is_valid():
        ListingImage.objects.create(
            listing=listing, uploaded_by=request.user, image=form.cleaned_data["image"],
            is_primary=not listing.images.exists(),
        )
        messages.success(request, "Photo added.")
    else:
        messages.error(request, " ".join(form.errors.get("image", ["Choose an image file."])))
    return redirect("listings:edit", pk=listing.pk)


def _own_image(request, image_pk):
    return get_object_or_404(ListingImage.objects.select_related("listing"), pk=image_pk, listing__seller=request.user)


@require_POST
@role_required(User.Role.SELLER)
def image_delete(request, image_pk):
    image = _own_image(request, image_pk)
    listing = image.listing
    remaining = listing.images.exclude(pk=image.pk)
    if listing.listing_status == Status.ACTIVE and not remaining.exists():
        messages.error(request, "A live listing needs at least one photo. Add another first or deactivate the listing.")
    else:
        was_primary = image.is_primary
        image.image.delete(save=False)
        image.delete()
        if was_primary and remaining.exists():
            first = remaining.first()
            first.is_primary = True
            first.save(update_fields=["is_primary"])
        messages.success(request, "Photo removed.")
    return redirect("listings:edit", pk=listing.pk)


@require_POST
@role_required(User.Role.SELLER)
def image_primary(request, image_pk):
    image = _own_image(request, image_pk)
    with transaction.atomic():
        image.listing.images.update(is_primary=False)
        image.is_primary = True
        image.save(update_fields=["is_primary"])
    messages.success(request, "Main photo changed.")
    return redirect("listings:edit", pk=image.listing_id)


# ---------- Admin: moderation (BR-29) ----------
@role_required(User.Role.ADMIN)
def admin_listings(request):
    qs = Listing.objects.select_related("seller", "category")
    current = request.GET.get("status", "")
    if current in Status.values:
        qs = qs.filter(listing_status=current)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(seller__email__icontains=q) | Q(seller__full_name__icontains=q))
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "listings/admin_list.html", {
        "page": page, "current": current, "q": q, "statuses": Status.choices, "querystring": params.urlencode(),
    })


@require_POST
@role_required(User.Role.ADMIN)
def admin_remove(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    listing.listing_status = Status.REMOVED
    listing.save(update_fields=["listing_status", "updated_at"])
    messages.success(request, f"“{listing.title}” was removed from the marketplace.")
    return _next_or(request, "listings:admin_list")


@require_POST
@role_required(User.Role.ADMIN)
def admin_restore(request, pk):
    listing = get_object_or_404(Listing, pk=pk, listing_status=Status.REMOVED)
    listing.listing_status = Status.INACTIVE
    listing.save(update_fields=["listing_status", "updated_at"])
    messages.success(request, f"“{listing.title}” was restored as inactive. The seller can reactivate it.")
    return _next_or(request, "listings:admin_list")
