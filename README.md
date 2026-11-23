# WornWorth: A Sustainable Secondhand Clothing Marketplace

CSIT327 Information Management II. Full-stack Django (templates) + PostgreSQL / Supabase. SQLite is not used.

## Features
**Standard features (Project Development 1):** account registration, login/logout, role-based dashboards (Buyer, Seller, Admin), user profile.

**Core feature (Project Development 2): Clothing Listings and Ordering.** The marketplace's main flow, end to end:

| Role | What they can do |
|------|------------------|
| Seller | Create, view, edit, publish/deactivate and delete clothing listings (title, category, size, condition, price, stock). Upload up to 6 photos, choose the main photo. See orders for their items, then confirm, process and ship them. |
| Buyer | Browse active listings with search, category/size/condition/price filters and sorting. Open an item, check out with a saved or new delivery address, track the order, cancel it while Pending or Confirmed, and confirm receipt once shipped. |
| Admin | Moderate all listings (remove or restore, BR-29) and monitor all orders. |

Business rules enforced (SDD numbering): BR-05 delivery info required, BR-06 one seller per listing, BR-07 listing needs details and a photo before publishing, BR-08 sellers edit only their own listings, BR-09/BR-12 only active listings with stock can be bought, BR-10/BR-14 stock never goes negative or oversold (row lock in a transaction), BR-11 no buying your own listing, BR-17 order total = subtotal + delivery fee, BR-18 price saved at purchase time, BR-19 unique order reference, BR-22/BR-23 cancel only while Pending/Confirmed, BR-29 only admins remove listings, BR-30 orders are kept when a listing is deactivated.

**Not in this phase:** shopping cart, online payments, delivery tracking numbers, reviews.

Data model (follows the SDD ERD): `users` → `listings` → `listing_images`; `categories` → `listings`; `users` → `addresses`; `users` → `orders` → `order_items` → `listings`.

## Setup
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then edit DB credentials
python manage.py makemigrations accounts listings orders
python manage.py migrate
python manage.py seed_demo                            # test accounts + clothing categories
python manage.py runserver
```
- **Local PostgreSQL:** run `createdb wornworth`, then fill the `DB_*` values in `.env`.
- **Supabase:** copy the connection string from Project Settings → Database into `DATABASE_URL` in `.env` (keep `?sslmode=require`).
- **Tests:** `python manage.py test`

## Test accounts (created by `seed_demo`, password `WornWorth#2026`)
| Role | Email |
|------|-------|
| Admin | admin@wornworth.test |
| Seller | seller@wornworth.test, seller2@wornworth.test |
| Buyer | buyer@wornworth.test, buyer2@wornworth.test |

Try it: log in as the seller → New listing (add a photo, Publish) → log in as the buyer → Browse → Buy → log in as the seller → confirm and ship → buyer confirms receipt.

## URLs
| Area | Path |
|------|------|
| Buyer | `/browse/`, `/listings/<id>/`, `/checkout/<listing_id>/`, `/orders/` |
| Seller | `/seller/listings/`, `/seller/listings/new/`, `/seller/listings/<id>/edit/`, `/orders/` |
| Admin | `/manage/listings/`, `/orders/`, `/dashboard/admin/` |

## Repository and branching
Repo name format `SystemName-Lastname-Firstname-Section`, public. `.env`, `venv/` and `__pycache__/` are git-ignored; `requirements.txt` is kept up to date. Branches: `main` (stable, PR only) ← `develop` ← `feature/*`. See `docs/GIT_WORKFLOW.md`.
