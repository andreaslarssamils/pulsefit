from django import forms


class NewsletterForm(forms.Form):
    """Footer newsletter signup — en e-postadress, skickas till Mailchimp via services.subscribe_email."""

    email = forms.EmailField()
