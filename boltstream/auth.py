from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class UsernameOrEmailModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        q = Q(username__iexact=username) | Q(email__iexact=username)
        user = User.objects.filter(q).first()
        if user and user.check_password(password) and user.is_active:
            return user
        else:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            User().set_password(password)
