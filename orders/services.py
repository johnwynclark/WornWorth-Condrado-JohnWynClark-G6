"""Order business logic. Every stock change happens inside a transaction with a row lock,
so two buyers can't oversell the same listing (SDD 4.3)."""
from django.conf import settings
from django.db import transaction
from django.db.models import F

from listings.models import Listing

from .models import Order, OrderItem


class OrderError(Exception):
    """A business-rule problem the user should see as a message."""


@transaction.atomic
def place_order(buyer, listing_id, quantity, address):
    listing = Listing.objects.select_for_update().get(pk=listing_id)
    if listing.seller_id == buyer.pk:
        raise OrderError("You can't buy your own listing.")  # BR-11
    if listing.listing_status != Listing.Status.ACTIVE:
        raise OrderError("This listing is no longer available.")  # BR-12
    if quantity < 1:
        raise OrderError("Quantity must be at least 1.")
    if quantity > listing.quantity:
        raise OrderError(f"Only {listing.quantity} left in stock.")  # BR-14
    if address.user_id != buyer.pk:
        raise OrderError("That delivery address isn't yours.")

    listing.quantity -= quantity
    listing.save(update_fields=["quantity", "updated_at"])

    subtotal = listing.price * quantity
    fee = settings.DELIVERY_FEE
    order = Order.objects.create(buyer=buyer, address=address, subtotal=subtotal, delivery_fee=fee, total_amount=subtotal + fee)  # BR-17
    OrderItem.objects.create(order=order, listing=listing, quantity=quantity, unit_price=listing.price, item_subtotal=subtotal)  # BR-18
    return order


@transaction.atomic
def cancel_order(order_pk):
    order = Order.objects.select_for_update().get(pk=order_pk)
    if not order.can_cancel:
        raise OrderError("This order can no longer be cancelled.")  # BR-22, BR-23
    for item in order.items.all():  # return stock
        Listing.objects.filter(pk=item.listing_id).update(quantity=F("quantity") + item.quantity)
    order.order_status = Order.Status.CANCELLED
    order.save(update_fields=["order_status"])
    return order


@transaction.atomic
def advance_order(order_pk):
    order = Order.objects.select_for_update().get(pk=order_pk)
    step = order.seller_next
    if step is None:
        raise OrderError("This order can't be moved forward by the seller.")
    order.order_status = step[0]
    order.save(update_fields=["order_status"])
    return order


@transaction.atomic
def complete_order(order_pk):
    order = Order.objects.select_for_update().get(pk=order_pk)
    if order.order_status != Order.Status.SHIPPED:
        raise OrderError("You can confirm receipt only after the order has shipped.")
    order.order_status = Order.Status.COMPLETED
    order.save(update_fields=["order_status"])
    return order
