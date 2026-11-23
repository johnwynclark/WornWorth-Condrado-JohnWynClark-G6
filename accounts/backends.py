from django.contrib.auth.backends import AllowAllUsersModelBackend


class ActiveAccountBackend(AllowAllUsersModelBackend):
    """Lets the login form explain that an account is suspended/deactivated,
    while still rejecting inactive users on every later request (BR-02)."""

    def get_user(self, user_id):
        user = super().get_user(user_id)
        return user if user is not None and user.is_active else None
