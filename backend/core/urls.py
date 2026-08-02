"""API routes.

The paths match what the React client already calls, so moving the backend to
Django changed only the port the client points at.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health),
    path("journeys", views.journeys),
    path("station/<str:code>", views.station),
    path("trains", views.trains),
    path("agent-logs", views.agent_logs),
    path("delays", views.report_delay),
    path("agents/run", views.run_agents),
]
