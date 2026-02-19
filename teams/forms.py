from django import forms
from allauth.account.forms import SignupForm

from .models import Event, Venue


class EventForm(forms.ModelForm):
    venue = forms.ModelChoiceField(
        queryset=Venue.objects.all().order_by("name"),
        empty_label="Select a venue",
    )
    starts_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    ends_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Event
        fields = [
            "title",
            "starts_at",
            "ends_at",
            "venue",
            "min_participants",
            "max_participants",
            "price",
        ]
        widgets = {}

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "End time must be after the start time.")
        return cleaned_data


class TopUpForm(forms.Form):
    amount = forms.DecimalField(
        min_value=1,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "1"}),
    )


class CustomSignupForm(SignupForm):
    full_name = forms.CharField(
        max_length=150,
        required=False,
        label="Full name",
        widget=forms.TextInput(attrs={"placeholder": "Jane Smith"}),
    )

    def save(self, request):
        user = super().save(request)
        full_name = (self.cleaned_data.get("full_name") or "").strip()
        if full_name:
            parts = full_name.split()
            user.first_name = parts[0]
            user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            user.save(update_fields=["first_name", "last_name"])
        return user
