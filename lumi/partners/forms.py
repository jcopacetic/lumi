from allauth.account.forms import SignupForm


class PartnerSignupForm(SignupForm):
    """
    Custom signup form for partners with Bootstrap 5 styling
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

            # Make email readonly (it's pre-filled from partner record)
            if field_name == "email":
                field.widget.attrs["readonly"] = True
                field.widget.attrs["class"] += " form-control-plaintext"

            # Add placeholder text
            if field_name == "password1":
                field.widget.attrs["placeholder"] = "Enter your password"
            elif field_name == "password2":
                field.widget.attrs["placeholder"] = "Confirm your password"
