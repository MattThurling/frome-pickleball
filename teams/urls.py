from django.urls import path

from . import views

app_name = "teams"

urlpatterns = [
    path("", views.TeamListView.as_view(), name="team-list"),
    path("wallet/", views.WalletView.as_view(), name="wallet"),
    path("wallet/topup/", views.WalletTopUpView.as_view(), name="wallet-topup"),
    path("teams/<int:team_id>/", views.TeamDetailView.as_view(), name="team-detail"),
    path(
        "teams/<int:team_id>/events/new/",
        views.EventCreateView.as_view(),
        name="event-create",
    ),
    path(
        "events/<int:event_id>/signup/",
        views.EventSignupToggleView.as_view(),
        name="event-signup",
    ),
    path("stripe/webhook/", views.StripeWebhookView.as_view(), name="stripe-webhook"),
]
