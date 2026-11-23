from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    """Login required, and the user's role must be one of `roles`.
    Wrong role -> sent to their own dashboard with an error message."""

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, "You don't have access to that page.")
                return redirect("accounts:dashboard")
            return view(request, *args, **kwargs)

        return login_required(wrapped)

    return decorator
