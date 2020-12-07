from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .viewsets import AuthorizeKeyAccessView, StreamViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("streams", StreamViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "authorize/<stream_uuid>",
        AuthorizeKeyAccessView.as_view(),
        name="authorize-key-access",
    ),
]
