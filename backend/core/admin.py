"""Register the tables with Django's admin.

This is a free win from moving to Django: the whole database, including the
agent log, becomes browsable at /admin without writing a single screen.
"""

from django.contrib import admin

from .models import (
    AgentLog,
    Arrival,
    Booking,
    Passenger,
    Platform,
    Station,
    StationManager,
    Train,
)


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "origin", "destination", "distance_km", "scheduled_halts")
    search_fields = ("name", "number")


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone",
        "nid_number",
        "nid_verified",
        "is_phone_verified",
    )
    list_filter = ("nid_verified", "is_phone_verified")
    # auth_token is a bearer credential - visible for debugging, not editable
    # by hand from here.
    readonly_fields = ("auth_token",)


@admin.register(StationManager)
class StationManagerAdmin(admin.ModelAdmin):
    """Read-only here by design - accounts are created via
    `manage.py create_manager`, not typed into the admin."""

    list_display = ("username", "created_at")
    readonly_fields = ("username", "password_hash", "auth_token", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "train",
        "passenger",
        "travel_date",
        "scheduled_departure",
        "expected_departure",
        "status",
        "delay_minutes",
        "recovered_minutes",
    )
    list_filter = ("status",)


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "passengers_on_site", "capacity")


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ("number", "station", "occupancy", "capacity", "last_alert_level")


@admin.register(Arrival)
class ArrivalAdmin(admin.ModelAdmin):
    list_display = ("train", "station", "scheduled", "expected", "platform", "status")


@admin.register(AgentLog)
class AgentLogAdmin(admin.ModelAdmin):
    """The audit trail, newest first."""

    list_display = ("id", "logged_at", "agent", "severity", "message")
    list_filter = ("agent", "severity")
    ordering = ("-id",)
