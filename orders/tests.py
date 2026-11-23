import shutil
import tempfile
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User
from listings.models import Category, Listing, ListingImage

from .models import Address, Order, OrderItem
from . import services

PW = "Str0ng-pass-93"
MEDIA = tempfile.mkdtemp()
ADDRESS = {"recipient_name": "Buy Er", "phone": "09171234567", "address_line": "12 Colon St", "city": "Cebu City", "province": "Cebu", "postal_code": "6000"}


def png():
    buf = BytesIO()
    Image.new("RGB", (10, 10), "blue").save(buf, "PNG")
    return SimpleUploadedFile("a.png", buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA)
class OrderTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cat = Category.objects.create(category_name="Jackets")
        self.seller = User.objects.create_user("s@x.com", PW, full_name="Sel Ler", role="SELLER")
        self.other_seller = User.objects.create_user("s2@x.com", PW, full_name="Sel Two", role="SELLER")
        self.buyer = User.objects.create_user("b@x.com", PW, full_name="Buy Er", role="BUYER")
        self.buyer2 = User.objects.create_user("b2@x.com", PW, full_name="Buy Two", role="BUYER")
        self.admin = User.objects.create_user("a@x.com", PW, full_name="Ad Min", role="ADMIN")
        self.listing = Listing.objects.create(seller=self.seller, category=cat, title="Denim jacket", description="Nice denim jacket.",
                                              price="650.00", size="L", condition="GOOD", quantity=3, listing_status="ACTIVE")
        ListingImage.objects.create(listing=self.listing, uploaded_by=self.seller, image=png(), is_primary=True)

    def checkout(self, qty=2, **extra):
        data = {"quantity": qty, **ADDRESS, **extra}
        return self.client.post(reverse("orders:checkout", args=[self.listing.pk]), data)

    def login(self, email):
        self.client.logout()
        self.client.login(username=email, password=PW)

    def test_checkout_creates_order_and_reduces_stock(self):
        self.login("b@x.com")
        self.assertEqual(self.checkout(2).status_code, 302)
        order = Order.objects.get()
        item = order.items.get()
        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(item.unit_price, Decimal("650.00"))
        self.assertEqual(order.subtotal, Decimal("1300.00"))
        self.assertEqual(order.total_amount, Decimal("1300.00") + Decimal("50.00"))  # BR-17
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.quantity, 1)
        self.assertEqual(Address.objects.filter(user=self.buyer).count(), 1)

    def test_price_snapshot_survives_price_change(self):
        self.login("b@x.com")
        self.checkout(1)
        self.listing.price = Decimal("900.00")
        self.listing.save()
        self.assertEqual(OrderItem.objects.get().unit_price, Decimal("650.00"))  # BR-18

    def test_cannot_oversell_or_buy_inactive(self):
        self.login("b@x.com")
        self.checkout(5)
        self.assertEqual(Order.objects.count(), 0)  # BR-14
        self.listing.listing_status = "INACTIVE"
        self.listing.save()
        self.checkout(1)
        self.assertEqual(Order.objects.count(), 0)  # BR-12

    def test_service_blocks_own_listing_and_foreign_address(self):
        addr = Address.objects.create(user=self.buyer, **ADDRESS)
        with self.assertRaises(services.OrderError):
            services.place_order(self.seller, self.listing.pk, 1, Address.objects.create(user=self.seller, **ADDRESS))  # BR-11
        with self.assertRaises(services.OrderError):
            services.place_order(self.buyer2, self.listing.pk, 1, addr)

    def test_missing_address_is_rejected(self):
        self.login("b@x.com")
        resp = self.client.post(reverse("orders:checkout", args=[self.listing.pk]), {"quantity": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)  # BR-05

    def test_cancel_restores_stock_and_blocks_after_shipping(self):
        self.login("b@x.com")
        self.checkout(2)
        order = Order.objects.get()
        self.client.post(reverse("orders:cancel", args=[order.pk]))
        order.refresh_from_db(); self.listing.refresh_from_db()
        self.assertEqual(order.order_status, "CANCELLED")
        self.assertEqual(self.listing.quantity, 3)
        order.order_status = "SHIPPED"; order.save()
        self.client.post(reverse("orders:cancel", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.order_status, "SHIPPED")  # BR-22

    def test_seller_flow_to_completed(self):
        self.login("b@x.com")
        self.checkout(1)
        order = Order.objects.get()
        self.login("s@x.com")
        for _ in range(3):
            self.client.post(reverse("orders:advance", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.order_status, "SHIPPED")
        self.login("b@x.com")
        self.client.post(reverse("orders:received", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.order_status, "COMPLETED")

    def test_order_visibility(self):
        self.login("b@x.com")
        self.checkout(1)
        order = Order.objects.get()
        url = reverse("orders:detail", args=[order.pk])
        for email, code in [("b@x.com", 200), ("s@x.com", 200), ("a@x.com", 200), ("b2@x.com", 404), ("s2@x.com", 404)]:
            self.login(email)
            self.assertEqual(self.client.get(url).status_code, code, email)
        self.login("s2@x.com")
        self.client.post(reverse("orders:advance", args=[order.pk]))  # not their order
        order.refresh_from_db()
        self.assertEqual(order.order_status, "PENDING")

    def test_seller_listing_with_orders_is_deactivated_not_deleted(self):
        self.login("b@x.com")
        self.checkout(1)
        self.login("s@x.com")
        self.client.post(reverse("listings:delete", args=[self.listing.pk]))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.listing_status, "INACTIVE")  # BR-30
        self.assertEqual(Order.objects.count(), 1)
