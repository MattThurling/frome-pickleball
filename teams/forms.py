from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    starts_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Event
        fields = [
            "title",
            "starts_at",
            "location",
            "min_participants",
            "max_participants",
            "price",
        ]
        widgets = {
            "location": forms.TextInput(attrs={"placeholder": "Gym, field, or link"}),
        }


class TopUpForm(forms.Form):
    amount = forms.DecimalField(
        min_value=1,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "1"}),
    )
