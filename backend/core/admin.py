"""Register the tables with Django's admin.

This is a free win from moving to Django: the whole database, including the
agent log, becomes browsable at /admin without writing a single screen.
"""

from django.contrib import admin

from .models import AgentLog, Arrival, Booking, Passenger, Platform, Station, Train


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "origin", "destination", "distance_km", "scheduled_halts")
    search_fields = ("name", "number")


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone")


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
