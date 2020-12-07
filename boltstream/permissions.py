from functools import wraps

from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.translation import gettext as _
from rest_framework.permissions import BasePermission


def require_rtmp_secret(view_func):
    @wraps(view_func)
    def _require_rtmp_secret(request, *args, **kwargs):
        if not RtmpSecretRequired().has_permission(request, None):
            return HttpResponseForbidden(_("Forbidden"))
        return view_func(request, *args, **kwargs)

    return _require_rtmp_secret


class RtmpSecretRequired(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.META["HTTP_X_RTMP_SECRET"] == settings.RTMP_SECRET
        except KeyError:
            return False
