"""NHCX-facing routes (G1). Mounted at the root and under `api/gateway/`."""

from django.urls import path

from care.nhcx.gateway import views

urlpatterns = [
    path("healthz", views.healthz, name="nhcx-healthz"),
    path("in/healthz", views.healthz, name="nhcx-in-healthz"),
    path("readyz", views.readyz, name="nhcx-readyz"),
    path("in/<path:path>", views.inbound, name="nhcx-inbound"),
    path("v1/<path:path>", views.inbound, {"prefix": "v1/"}, name="nhcx-inbound-v1"),
]
