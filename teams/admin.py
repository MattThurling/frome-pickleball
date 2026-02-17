from django.contrib import admin

from .models import (
    Event,
    EventSignup,
    Team,
    TeamMembership,
    Venue,
    Wallet,
    WalletTransaction,
)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role", "joined_at")
    list_filter = ("role", "team")
    search_fields = ("team__name", "user__username", "user__email")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "team",
        "starts_at",
        "ends_at",
        "venue",
        "max_participants",
        "price",
    )
    list_filter = ("team",)
    search_fields = ("title", "team__name")


@admin.register(EventSignup)
class EventSignupAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "status", "created_at")
    list_filter = ("event__team", "status")


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "postcode")
    search_fields = ("name", "address_line1", "city", "postcode")


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "updated_at")
    search_fields = ("user__username", "user__email")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "kind", "amount", "event", "created_at")
    list_filter = ("kind",)
