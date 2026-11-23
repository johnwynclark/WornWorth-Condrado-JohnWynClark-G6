from django.core.management.base import BaseCommand

from accounts.models import User
from listings.models import Category

PASSWORD = "WornWorth#2026"
ACCOUNTS = [
    ("admin@wornworth.test", "Demo Admin", "ADMIN"),
    ("seller@wornworth.test", "Demo Seller", "SELLER"),
    ("seller2@wornworth.test", "Second Seller", "SELLER"),
    ("buyer@wornworth.test", "Demo Buyer", "BUYER"),
    ("buyer2@wornworth.test", "Second Buyer", "BUYER"),
]
CATEGORIES = [
    ("Shirts & Tops", "T-shirts, blouses, polos and button-ups"),
    ("Pants & Shorts", "Jeans, trousers, shorts and skirts"),
    ("Dresses", "Casual, formal and party dresses"),
    ("Jackets & Outerwear", "Jackets, coats, hoodies and cardigans"),
    ("Shoes & Accessories", "Footwear, bags, belts and hats"),
]


class Command(BaseCommand):
    help = "Create demo test accounts and clothing categories (safe to run more than once)."

    def handle(self, *args, **options):
        for name, desc in CATEGORIES:
            Category.objects.get_or_create(category_name=name, defaults={"description": desc})
        for email, full_name, role in ACCOUNTS:
            if User.objects.filter(email=email).exists():
                continue
            if role == "ADMIN":
                User.objects.create_superuser(email=email, password=PASSWORD, full_name=full_name)
            else:
                User.objects.create_user(email=email, password=PASSWORD, full_name=full_name, role=role)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(CATEGORIES)} categories and demo accounts (password: {PASSWORD})."))
