from django import forms


class CustomSignupForm(forms.Form):
    """
        Adds a 'Full Name' field to allauth's signup form.
    """

    name = forms.CharField(
        max_length=150,
        label="Full Name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Your name",
                "autofocus": True}),
    )

    field_order = ["name", "email", "password1", "password2"]

    def signup(self, request, user):
        full_name = self.cleaned_data["name"].strip()
        first_name, _, last_name = full_name.partition(" ")
        user.first_name = first_name
        user.last_name = last_name
        user.save()
