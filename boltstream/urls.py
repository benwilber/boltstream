"""boltstream URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path("", views.home, name="home")
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path("", Home.as_view(), name="home")
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path("blog/", include("blog.urls"))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from .views import (
    FeedManifestView,
    FeedWebVTTView,
    HomeView,
    MasterManifestView,
    ProfileView,
    UserView,
    api_redirect,
    authorize_channel_access,
    authorize_channel_message,
    expire_viewers,
    health_check,
    start_stream,
    stop_stream,
)


def fake_view(request):
    pass


urlpatterns = [
    re_path(r"^$", HomeView.as_view(), name="home"),
    path("sign-in", auth_views.LoginView.as_view(), name="login"),
    path("sign-out", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "change-password",
        auth_views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "change-password-done",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path(
        "reset-password", auth_views.PasswordResetView.as_view(), name="password_reset"
    ),
    path(
        "reset-password-done",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset-password/<uidb64>/<token>",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset-password-done",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("app-health", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/<version>/", include("boltstream.apiurls")),
    path("api/auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/", api_redirect),
    path(
        "authorize_channel_access",
        authorize_channel_access,
        name="authorize-channel-access",
    ),
    path(
        "authorize_channel_message",
        authorize_channel_message,
        name="authorize-channel-message",
    ),
    path(
        "privacy",
        TemplateView.as_view(template_name="boltstream/privacy.html"),
        name="privacy",
    ),
    path(
        "terms",
        TemplateView.as_view(template_name="boltstream/terms.html"),
        name="terms",
    ),
    path(
        "dmca", TemplateView.as_view(template_name="boltstream/dmca.html"), name="dmca"
    ),
    path("start-stream", start_stream, name="start-stream"),
    path("stop-stream", stop_stream, name="stop-stream"),
    path("expire-viewers", expire_viewers, name="expire-viewers"),
    path("stream-info", fake_view, name="stream-info"),
    path("stream-control/drop/publisher", fake_view, name="drop-stream"),
    path("offline.mp4", fake_view, name="stream-offline"),
    path(
        "live/<uuid>/master.m3u8", MasterManifestView.as_view(), name="master-manifest"
    ),
    path("live/<uuid>/index.m3u8", fake_view, name="index-manifest"),
    path("live/<uuid>/preview.jpg", fake_view, name="stream-image"),
    path("live/<uuid>/preview.mp4", fake_view, name="stream-preview"),
    path("feed/<uuid>.m3u8", FeedManifestView.as_view(), name="feed-manifest"),
    path("feed/<uuid>.vtt", FeedWebVTTView.as_view(), name="feed-webvtt"),
    path("channel/<uuid>", fake_view, name="stream-channel"),
    path("~<username>/profile", ProfileView.as_view(), name="profile"),
    path("~<username>/<stream_uuid>", UserView.as_view(), name="stream"),
    path("~<username>/<stream_uuid>/<stream_slug>", UserView.as_view(), name="stream"),
    path("~<username>", UserView.as_view(), name="user"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
