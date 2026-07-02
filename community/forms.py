from django import forms

from .models import CommunityPost


class CommunityPostForm(forms.ModelForm):
    """Composer for the community feed (US-23)."""

    class Meta:
        model = CommunityPost
        fields = ["body"]
        labels = {"body": "Share something"}
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Share your progress, a tip or a question...",
                }
            )
        }
