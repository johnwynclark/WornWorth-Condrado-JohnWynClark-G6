from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import LoginForm, ProfileForm, RegistrationForm
from .models import User

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
    return render(request, "dashboards/buyer.html")


@role_required(User.Role.SELLER)
def seller_dashboard(request):
    return render(request, "dashboards/seller.html")


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "buyer_count": User.objects.filter(role=User.Role.BUYER).count(),
        "seller_count": User.objects.filter(role=User.Role.SELLER).count(),
        "suspended_count": User.objects.exclude(account_status=User.Status.ACTIVE).count(),
        "recent_users": User.objects.order_by("-created_at")[:8],
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
