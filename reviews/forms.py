from django import forms

from .models import Review

RATING_CHOICES = [(i, "★" * i) for i in range(5, 0, -1)]


class ReviewForm(forms.ModelForm):
    """Rating (1–5) + written review (US-28)."""

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        label="Rating")

    class Meta:
        model = Review
        fields = ["rating", "body"]
        labels = {"body": "Your review"}
        widgets = {
            "body": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Share your experience..."}
            ),
        }
