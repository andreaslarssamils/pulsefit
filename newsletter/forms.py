from django import forms


class NewsletterForm(forms.Form):
    """Footer newsletter signup.

    En e-postadress, skickas till Mailchimp via
    services.subscribe_email.
    """

    email = forms.EmailField()
