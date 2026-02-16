from django.urls import path

from . import views

app_name = "teams"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("wallet/", views.WalletView.as_view(), name="wallet"),
    path(
        "events/new/",
        views.EventCreateView.as_view(),
        name="event-create",
    ),
    path("events/<int:event_id>/", views.EventDetailView.as_view(), name="event-detail"),
    path(
        "events/<int:event_id>/signup/",
        views.EventSignupToggleView.as_view(),
        name="event-signup",
    ),
    path("stripe/webhook/", views.StripeWebhookView.as_view(), name="stripe-webhook"),
]
