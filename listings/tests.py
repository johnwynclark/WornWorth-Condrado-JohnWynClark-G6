import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User

from .models import Category, Listing, ListingImage

PW = "Str0ng-pass-93"
MEDIA = tempfile.mkdtemp()


def png(name="a.png"):
    buf = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA)
class ListingTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.cat = Category.objects.create(category_name="Shirts")
        self.seller = User.objects.create_user("s@x.com", PW, full_name="Sel Ler", role="SELLER")
        self.other = User.objects.create_user("o@x.com", PW, full_name="Oth Er", role="SELLER")
        self.buyer = User.objects.create_user("b@x.com", PW, full_name="Buy Er", role="BUYER")
        self.admin = User.objects.create_user("a@x.com", PW, full_name="Ad Min", role="ADMIN")

    def data(self, **kw):
        base = {"category": self.cat.pk, "title": "Linen shirt", "description": "Soft linen, no flaws.", "price": "320.00",
                "size": "M", "condition": "GOOD", "quantity": "2"}
        base.update(kw)
        return base

    def make_listing(self, seller=None, status="ACTIVE", with_image=True, qty=2):
        listing = Listing.objects.create(seller=seller or self.seller, category=self.cat, title="Denim jacket", description="Nice denim jacket.",
                                         price="650.00", size="L", condition="GOOD", quantity=qty, listing_status=status)
        if with_image:
            ListingImage.objects.create(listing=listing, uploaded_by=listing.seller, image=png(), is_primary=True)
        return listing

    def test_publish_requires_photo(self):
        self.client.login(username="s@x.com", password=PW)
        resp = self.client.post(reverse("listings:create"), self.data(action="publish"))
        self.assertContains(resp, "Add a main photo before publishing")
        self.assertEqual(Listing.objects.count(), 0)

    def test_create_published_listing_with_photo(self):
        self.client.login(username="s@x.com", password=PW)
        self.client.post(reverse("listings:create"), self.data(action="publish", image=png()))
        listing = Listing.objects.get()
        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.listing_status, "ACTIVE")
        self.assertEqual(listing.images.count(), 1)

    def test_draft_without_photo_and_validation(self):
        self.client.login(username="s@x.com", password=PW)
        self.client.post(reverse("listings:create"), self.data(action="draft"))
        self.assertEqual(Listing.objects.get().listing_status, "DRAFT")
        resp = self.client.post(reverse("listings:create"), self.data(action="draft", price="0"))
        self.assertEqual(Listing.objects.count(), 1)
        self.assertEqual(resp.status_code, 200)

    def test_seller_cannot_touch_others_listing(self):
        listing = self.make_listing(seller=self.other)
        self.client.login(username="s@x.com", password=PW)
        self.assertEqual(self.client.get(reverse("listings:edit", args=[listing.pk])).status_code, 404)
        self.client.post(reverse("listings:delete", args=[listing.pk]))
        self.assertTrue(Listing.objects.filter(pk=listing.pk).exists())

    def test_edit_and_delete_own_listing(self):
        listing = self.make_listing()
        self.client.login(username="s@x.com", password=PW)
        self.client.post(reverse("listings:edit", args=[listing.pk]), self.data(title="Updated title", quantity="5"))
        listing.refresh_from_db()
        self.assertEqual((listing.title, listing.quantity), ("Updated title", 5))
        self.client.post(reverse("listings:delete", args=[listing.pk]))
        self.assertFalse(Listing.objects.filter(pk=listing.pk).exists())

    def test_browse_only_shows_active_in_stock(self):
        self.make_listing(status="ACTIVE")
        self.make_listing(status="DRAFT")
        self.make_listing(status="ACTIVE", qty=0)
        self.client.login(username="b@x.com", password=PW)
        resp = self.client.get(reverse("listings:browse"))
        self.assertEqual(len(resp.context["page"].object_list), 1)

    def test_browse_filters(self):
        self.make_listing()
        self.client.login(username="b@x.com", password=PW)
        self.assertEqual(len(self.client.get(reverse("listings:browse"), {"q": "denim"}).context["page"].object_list), 1)
        self.assertEqual(len(self.client.get(reverse("listings:browse"), {"q": "zzz"}).context["page"].object_list), 0)
        self.assertEqual(len(self.client.get(reverse("listings:browse"), {"min_price": "700"}).context["page"].object_list), 0)

    def test_role_access(self):
        listing = self.make_listing()
        self.client.login(username="b@x.com", password=PW)
        self.assertEqual(self.client.get(reverse("listings:my_listings")).status_code, 302)  # buyer blocked
        self.client.logout()
        self.client.login(username="s@x.com", password=PW)
        self.assertEqual(self.client.get(reverse("listings:browse")).status_code, 302)  # seller blocked
        self.client.logout()
        self.assertEqual(self.client.get(reverse("listings:detail", args=[listing.pk])).status_code, 302)  # anonymous

    def test_admin_remove_hides_listing(self):
        listing = self.make_listing()
        self.client.login(username="a@x.com", password=PW)
        self.client.post(reverse("listings:admin_remove", args=[listing.pk]))
        listing.refresh_from_db()
        self.assertEqual(listing.listing_status, "REMOVED")
        self.client.logout()
        self.client.login(username="b@x.com", password=PW)
        self.assertEqual(self.client.get(reverse("listings:detail", args=[listing.pk])).status_code, 404)

    def test_seller_cannot_moderate(self):  # BR-29
        listing = self.make_listing()
        self.client.login(username="s@x.com", password=PW)
        self.client.post(reverse("listings:admin_remove", args=[listing.pk]))
        listing.refresh_from_db()
        self.assertEqual(listing.listing_status, "ACTIVE")
