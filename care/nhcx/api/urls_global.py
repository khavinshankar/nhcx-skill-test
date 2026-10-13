"""NHCX routes outside facility scope, mounted at /api/v1/nhcx/ (api/CONTRACT.md)."""

from django.urls import path

from care.nhcx.api import views_global as v

urlpatterns = [
    path(
        "practitioner/<str:user_id>/",
        v.PractitionerProfileView.as_view(),
        name="nhcx-practitioner",
    ),
    path("abha/<str:action>/", v.AbhaView.as_view(), name="nhcx-abha"),
]
