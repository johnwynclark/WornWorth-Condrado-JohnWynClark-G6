from django.test import TestCase
from django.urls import reverse

from .models import User

PW = "Str0ng-pass-93"


class AccountTests(TestCase):
    def make(self, email, role="BUYER", **kw):
        return User.objects.create_user(email=email, password=PW, full_name="Test User", role=role, **kw)

    def test_register_hashes_password_and_rejects_duplicates(self):
        data = {"full_name": "Ana Cruz", "email": "ana@example.com", "phone": "", "role": "BUYER", "password1": PW, "password2": PW}
        self.assertRedirects(self.client.post(reverse("accounts:register"), data), reverse("accounts:login"))
        user = User.objects.get(email="ana@example.com")
        self.assertNotEqual(user.password, PW)
        self.assertTrue(user.check_password(PW))
        data["email"] = "ANA@example.com"
        self.assertEqual(self.client.post(reverse("accounts:register"), data).status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch_rejected(self):
        data = {"full_name": "Ana Cruz", "email": "a@example.com", "role": "BUYER", "password1": PW, "password2": "different"}
        self.client.post(reverse("accounts:register"), data)
        self.assertFalse(User.objects.exists())

    def test_login_redirects_by_role_and_bad_login_fails(self):
        self.make("seller@example.com", "SELLER")
        resp = self.client.post(reverse("accounts:login"), {"username": "seller@example.com", "password": PW}, follow=True)
        self.assertEqual(resp.redirect_chain[-1][0], reverse("accounts:seller_dashboard"))
        self.client.post(reverse("accounts:logout"))
        resp = self.client.post(reverse("accounts:login"), {"username": "seller@example.com", "password": "nope"})
        self.assertContains(resp, "Incorrect email or password")

    def test_protected_pages_redirect_anonymous(self):
        for name in ("dashboard", "buyer_dashboard", "profile", "profile_edit"):
            resp = self.client.get(reverse(f"accounts:{name}"))
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse("accounts:login"), resp.url)

    def test_role_isolation(self):
        self.make("buyer@example.com", "BUYER")
        self.client.login(username="buyer@example.com", password=PW)
        for name in ("seller_dashboard", "admin_dashboard"):
            resp = self.client.get(reverse(f"accounts:{name}"), follow=True)
            self.assertEqual(resp.redirect_chain[-1][0], reverse("accounts:buyer_dashboard"))

    def test_suspended_user_cannot_login(self):
        self.make("bad@example.com", account_status="SUSPENDED")
        resp = self.client.post(reverse("accounts:login"), {"username": "bad@example.com", "password": PW})
        self.assertContains(resp, "suspended or deactivated")

    def test_profile_update_and_email_uniqueness(self):
        self.make("one@example.com")
        self.make("two@example.com")
        self.client.login(username="one@example.com", password=PW)
        resp = self.client.post(reverse("accounts:profile_edit"), {"full_name": "New Name", "email": "two@example.com", "phone": ""})
        self.assertEqual(resp.status_code, 200)
        self.client.post(reverse("accounts:profile_edit"), {"full_name": "New Name", "email": "one@example.com", "phone": "09171234567"})
        self.assertEqual(User.objects.get(email="one@example.com").full_name, "New Name")
