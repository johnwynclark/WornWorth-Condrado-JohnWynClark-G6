# WornWorth: Account Feature (IM2 Phase 1)

Full-stack Django (templates) + PostgreSQL/Supabase. SQLite is not configured anywhere.

## Setup
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then edit DB credentials
python manage.py makemigrations accounts
python manage.py migrate
python manage.py createsuperuser                      # creates an ADMIN-role user
python manage.py runserver
```

**Local PostgreSQL:** create the database first (`createdb wornworth`) and fill the `DB_*` values.
**Supabase:** copy the connection string from Project Settings → Database and set `DATABASE_URL` in `.env` (keep `?sslmode=require`).

Run tests: `python manage.py test accounts`

## Roles and dashboards (from the SDD `USERS.role` enum)
| Role   | URL                  | How it's created |
|--------|----------------------|------------------|
| BUYER  | `/dashboard/buyer/`  | Registration form |
| SELLER | `/dashboard/seller/` | Registration form |
| ADMIN  | `/dashboard/admin/`  | `createsuperuser` or Django admin (`/django-admin/`) |

`/dashboard/` sends each user to their own dashboard. Opening another role's URL redirects back to your own with an error message.

## Feature map
- Registration, login, logout: `accounts/forms.py`, `accounts/views.py`
- Role protection: `accounts/decorators.py` (`@role_required`)
- Custom user model (email login, hashed password, role, account_status): `accounts/models.py`
- Suspended/deactivated accounts cannot log in (BR-02): `accounts/backends.py`
- Profile view/edit (own profile only; no user id in the URL): `profile/`, `profile/edit/`

## GitHub repository requirements
- **Repository name:** `WornWorth-Condrado-JohnWynClark-<Section>` (format `SystemName-Lastname-Firstname-Section`; replace `<Section>` with your section code, e.g. `G01`). Adjust the name order if your first/last name split differs.
- **Visibility:** Public.
- **Secrets:** `.env` is in `.gitignore`, as are `venv/` and `__pycache__/`. Only `.env.example` (placeholders, no real values) is committed. If a real key ever gets committed, rotate it in Supabase immediately; deleting the file later does not remove it from history.
- **requirements.txt:** included.

### Setting up the repo and committing regularly
```bash
git init -b main
git add .gitignore requirements.txt .env.example README.md
git commit -m "Initial commit: gitignore, requirements, README"
git remote add origin https://github.com/<your-username>/WornWorth-Condrado-JohnWynClark-<Section>.git
git push -u origin main
```
Then commit and push as you finish each piece, not all at the end. A sensible sequence for this phase:
1. `Set up Django project and PostgreSQL/Supabase settings`
2. `Add custom User model, manager, and admin`
3. `Add registration form, view, and template`
4. `Add login and logout with error messages`
5. `Add role_required decorator and role-based dashboards`
6. `Add profile view and edit`
7. `Add styles and base template`
8. `Add account tests`

Before every push, run `git status` and confirm `.env` is not listed.
