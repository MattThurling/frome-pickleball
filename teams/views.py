from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import CharField, Count, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.views.generic import CreateView, DetailView

from .forms import EventForm, TopUpForm
from .models import (
    Event,
    EventSignup,
    Team,
    TeamMembership,
    Wallet,
    WalletTransaction,
)

try:
    import stripe
except ImportError:  # pragma: no cover - handled with a user-facing message
    stripe = None


def get_default_team():
    team, _ = Team.objects.get_or_create(name=settings.TEAM_NAME)
    return team


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        team = get_default_team()
        TeamMembership.objects.get_or_create(
            team=team,
            user=request.user,
            defaults={"role": TeamMembership.Role.MEMBER},
        )
        user_status = EventSignup.objects.filter(
            event=OuterRef("pk"), user=request.user
        ).values("status")[:1]
        events = (
            team.events.annotate(
                yes_count=Count(
                    "signups",
                    filter=Q(signups__status=EventSignup.Status.YES),
                ),
                waitlist_count=Count(
                    "signups",
                    filter=Q(signups__status=EventSignup.Status.WAITLIST),
                ),
                my_status=Subquery(user_status, output_field=CharField()),
            )
            .select_related("created_by", "venue")
            .order_by("starts_at")
        )
        my_events = events.filter(
            signups__user=request.user, signups__status=EventSignup.Status.YES
        ).distinct()
        is_admin = team.memberships.filter(
            user=request.user, role=TeamMembership.Role.ADMIN
        ).exists()
        return render(
            request,
            "teams/team_detail.html",
            {
                "team": team,
                "events": events,
                "my_events": my_events,
                "is_admin": is_admin,
            },
        )


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "teams/event_detail.html"
    context_object_name = "event"
    pk_url_kwarg = "event_id"

    def get_queryset(self):
        team = get_default_team()
        return (
            Event.objects.filter(team=team)
            .select_related("team", "venue")
            .annotate(
                waitlist_count=Count(
                    "signups",
                    filter=Q(signups__status=EventSignup.Status.WAITLIST),
                )
            )
            .prefetch_related("signups__user")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        TeamMembership.objects.get_or_create(
            team=event.team,
            user=self.request.user,
            defaults={"role": TeamMembership.Role.MEMBER},
        )
        signups = event.signups.select_related("user").order_by("created_at")
        context["signups_yes"] = signups.filter(status=EventSignup.Status.YES)
        context["signups_waitlist"] = signups.filter(
            status=EventSignup.Status.WAITLIST
        )
        context["signups_maybe"] = signups.filter(status=EventSignup.Status.MAYBE)
        context["signups_no"] = signups.filter(status=EventSignup.Status.NO)
        context["my_status"] = (
            signups.filter(user=self.request.user)
            .values_list("status", flat=True)
            .first()
        )
        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "teams/event_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.team = get_default_team()
        is_admin = TeamMembership.objects.filter(
            team=self.team, user=request.user, role=TeamMembership.Role.ADMIN
        ).exists()
        if not is_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["team"] = self.team
        return context

    def form_valid(self, form):
        form.instance.team = self.team
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("teams:home")


class EventSignupToggleView(LoginRequiredMixin, View):
    def post(self, request, event_id):
        event = get_object_or_404(Event.objects.select_related("team"), pk=event_id)
        TeamMembership.objects.get_or_create(
            team=event.team,
            user=request.user,
            defaults={"role": TeamMembership.Role.MEMBER},
        )

        requested_status = request.POST.get("status")
        if not requested_status:
            requested_status = (
                EventSignup.Status.YES
                if request.POST.get("signup") == "1"
                else EventSignup.Status.NO
            )
        if requested_status not in EventSignup.Status.values:
            messages.error(request, "Invalid response.")
            return redirect("teams:home")

        with transaction.atomic():
            event = (
                Event.objects.select_for_update()
                .select_related("team")
                .get(pk=event_id)
            )
            signup = (
                EventSignup.objects.select_for_update()
                .filter(event=event, user=request.user)
                .first()
            )
            current_status = signup.status if signup else None
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

            yes_count = EventSignup.objects.filter(
                event=event, status=EventSignup.Status.YES
            ).count()
            spots_left = event.max_participants - yes_count

            message_sent = False

            if (
                requested_status == EventSignup.Status.YES
                and current_status != EventSignup.Status.YES
            ):
                if spots_left <= 0:
                    requested_status = EventSignup.Status.WAITLIST
                    messages.info(
                        request, "Event is full. You've been added to the waitlist."
                    )
                    message_sent = True
                elif event.price > 0 and wallet.balance < event.price:
                    messages.error(
                        request,
                        "Insufficient wallet balance. Top up to book this event.",
                    )
                    return redirect("teams:home")

            if signup:
                signup.status = requested_status
                signup.save(update_fields=["status"])
            else:
                signup = EventSignup.objects.create(
                    event=event, user=request.user, status=requested_status
                )

            if (
                current_status == EventSignup.Status.YES
                and requested_status != EventSignup.Status.YES
            ):
                if event.price > 0:
                    wallet.balance = wallet.balance + event.price
                    wallet.save(update_fields=["balance"])
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=event.price,
                        kind=WalletTransaction.Kind.EVENT_REFUND,
                        event=event,
                    )
                self._promote_waitlist(event, exclude_user_id=request.user.id)

            if (
                current_status != EventSignup.Status.YES
                and requested_status == EventSignup.Status.YES
            ):
                if event.price > 0:
                    wallet.balance = wallet.balance - event.price
                    wallet.save(update_fields=["balance"])
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=-event.price,
                        kind=WalletTransaction.Kind.EVENT_DEBIT,
                        event=event,
                    )

            if not message_sent and current_status != requested_status:
                if requested_status == EventSignup.Status.YES:
                    messages.success(request, "You're booked in!")
                elif requested_status == EventSignup.Status.WAITLIST:
                    messages.info(request, "You're on the waitlist.")
                elif requested_status == EventSignup.Status.MAYBE:
                    messages.info(request, "Marked as maybe.")
                elif requested_status == EventSignup.Status.NO:
                    messages.info(request, "Marked as not attending.")

        return redirect("teams:home")

    @staticmethod
    def _promote_waitlist(event, exclude_user_id=None):
        yes_count = EventSignup.objects.filter(
            event=event, status=EventSignup.Status.YES
        ).count()
        spots_left = event.max_participants - yes_count
        if spots_left <= 0:
            return

        waitlist = (
            EventSignup.objects.select_for_update()
            .filter(event=event, status=EventSignup.Status.WAITLIST)
            .exclude(user_id=exclude_user_id)
            .order_by("created_at")
        )

        for signup in waitlist:
            if spots_left <= 0:
                break
            wallet, _ = Wallet.objects.get_or_create(user=signup.user)
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

            if event.price > 0 and wallet.balance < event.price:
                continue

            signup.status = EventSignup.Status.YES
            signup.save(update_fields=["status"])
            if event.price > 0:
                wallet.balance = wallet.balance - event.price
                wallet.save(update_fields=["balance"])
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=-event.price,
                    kind=WalletTransaction.Kind.EVENT_DEBIT,
                    event=event,
                )
            spots_left -= 1


class WalletView(LoginRequiredMixin, View):
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        session_id = request.GET.get("session_id")
        if session_id:
            if not settings.STRIPE_SECRET_KEY or stripe is None:
                messages.error(request, "Stripe is not configured yet.")
                return redirect("teams:wallet")

            stripe.api_key = settings.STRIPE_SECRET_KEY
            try:
                session = stripe.checkout.Session.retrieve(session_id)
            except stripe.error.StripeError:
                messages.error(request, "Unable to verify the Stripe session.")
                return redirect("teams:wallet")

            session_user_id = session.get("client_reference_id") or session.get(
                "metadata", {}
            ).get("user_id")
            if str(session_user_id) != str(request.user.id):
                messages.error(request, "This top-up session does not belong to you.")
                return redirect("teams:wallet")

            if session.get("payment_status") != "paid":
                messages.info(request, "Payment is not complete yet.")
                return redirect("teams:wallet")

            amount_total = session.get("amount_total")
            if amount_total is None:
                messages.error(request, "Stripe did not return a payment amount.")
                return redirect("teams:wallet")

            payment_intent = session.get("payment_intent")
            amount = Decimal(amount_total) / Decimal("100")
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
                already_logged = WalletTransaction.objects.filter(
                    stripe_session_id=session_id
                ).exists()
                if not already_logged:
                    wallet.balance = wallet.balance + amount
                    wallet.save(update_fields=["balance"])
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=amount,
                        kind=WalletTransaction.Kind.TOPUP,
                        stripe_session_id=session_id,
                        stripe_payment_intent=payment_intent or None,
                    )
                    messages.success(request, "Top-up applied to your wallet.")
                else:
                    messages.info(request, "Top-up was already applied.")
            return redirect("teams:home")
        form = TopUpForm()
        return render(request, "teams/wallet.html", {"wallet": wallet, "form": form})

    def post(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        if not settings.STRIPE_SECRET_KEY:
            messages.error(request, "Stripe is not configured yet.")
            return redirect("teams:wallet")
        if stripe is None:
            messages.error(request, "Stripe package is not installed on the server.")
            return redirect("teams:wallet")

        form = TopUpForm(request.POST)
        if not form.is_valid():
            return render(
                request, "teams/wallet.html", {"wallet": wallet, "form": form}
            )

        amount = form.cleaned_data["amount"]
        if amount <= 0:
            messages.error(request, "Top up amount must be greater than zero.")
            return render(
                request, "teams/wallet.html", {"wallet": wallet, "form": form}
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY
        amount_cents = int(amount * Decimal("100"))
        success_url = request.build_absolute_uri(reverse("teams:wallet"))
        success_url = f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.build_absolute_uri(reverse("teams:wallet"))

        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": settings.STRIPE_CURRENCY,
                        "product_data": {"name": "Wallet top-up"},
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(request.user.id),
            metadata={"user_id": str(request.user.id)},
        )
        return redirect(session.url)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET or stripe is None:
            return HttpResponse(status=400)

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)
        except ValueError:
            return HttpResponse(status=400)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            if session.get("payment_status") != "paid":
                return HttpResponse(status=200)

            user_id = session.get("client_reference_id") or session.get("metadata", {}).get(
                "user_id"
            )
            amount_total = session.get("amount_total")
            session_id = session.get("id")
            payment_intent = session.get("payment_intent", "")

            if not user_id or amount_total is None or not session_id:
                return HttpResponse(status=200)

            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                return HttpResponse(status=200)

            User = get_user_model()
            if not User.objects.filter(pk=user_id).exists():
                return HttpResponse(status=200)

            amount = Decimal(amount_total) / Decimal("100")
            wallet, _ = Wallet.objects.get_or_create(user_id=user_id)

            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
                already_logged = WalletTransaction.objects.filter(
                    stripe_session_id=session_id
                ).exists()
                if not already_logged:
                    wallet.balance = wallet.balance + amount
                    wallet.save(update_fields=["balance"])
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=amount,
                        kind=WalletTransaction.Kind.TOPUP,
                        stripe_session_id=session_id,
                        stripe_payment_intent=payment_intent or None,
                    )

        return HttpResponse(status=200)
