"""URL configuration for the RailBot BD project.

Everything the dashboards call lives under /api/, handled by the core app.
The Django admin is kept because it gives a ready-made way to inspect the
tables and the agent log during a demo.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]
