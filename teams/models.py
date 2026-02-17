from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Team(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Venue(models.Model):
    name = models.CharField(max_length=140)
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    postcode = models.CharField(max_length=20)
    url = models.URLField(blank=True)
    info = models.TextField(blank=True)

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    team = models.ForeignKey(Team, related_name="memberships", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="team_memberships", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="unique_team_member"),
        ]

    def __str__(self):
        return f"{self.user} on {self.team} ({self.role})"


class Event(models.Model):
    team = models.ForeignKey(Team, related_name="events", on_delete=models.CASCADE)
    title = models.CharField(max_length=140)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    venue = models.ForeignKey(
        Venue, related_name="events", on_delete=models.SET_NULL, null=True, blank=True
    )
    min_participants = models.PositiveIntegerField(default=0)
    max_participants = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="created_events", on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(check=Q(max_participants__gte=1), name="event_max_gte_1"),
            models.CheckConstraint(
                check=Q(min_participants__lte=F("max_participants")),
                name="event_min_lte_max",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.team})"

    @property
    def spots_taken(self):
        if hasattr(self, "yes_count"):
            return self.yes_count
        if hasattr(self, "signup_count"):
            return self.signup_count
        return self.signups.filter(status=EventSignup.Status.YES).count()

    @property
    def spots_left(self):
        return max(self.max_participants - self.spots_taken, 0)

    @property
    def is_full(self):
        return self.spots_left <= 0


class EventSignup(models.Model):
    class Status(models.TextChoices):
        YES = "yes", "Yes"
        MAYBE = "maybe", "Maybe"
        NO = "no", "No"
        WAITLIST = "waitlist", "Waitlist"

    event = models.ForeignKey(Event, related_name="signups", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="event_signups", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.YES
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="unique_event_signup"),
        ]

    def __str__(self):
        return f"{self.user} -> {self.event} ({self.status})"


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="wallet", on_delete=models.CASCADE
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} wallet"


class WalletTransaction(models.Model):
    class Kind(models.TextChoices):
        TOPUP = "topup", "Top up"
        EVENT_DEBIT = "event_debit", "Event debit"
        EVENT_REFUND = "event_refund", "Event refund"

    wallet = models.ForeignKey(
        Wallet, related_name="transactions", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL)
    stripe_session_id = models.CharField(
        max_length=255, blank=True, null=True, unique=True
    )
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user} {self.kind} {self.amount}"
