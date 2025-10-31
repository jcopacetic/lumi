from allauth.account.forms import SignupForm
from django import forms
from django.core.exceptions import ValidationError

from .models import Partner

phone_number_digits = 10


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


class PartnerProfileForm(forms.ModelForm):
    """
    Form for partners to update their profile information in settings.
    This includes both primary contact and company information that syncs to HubSpot.
    """

    class Meta:
        model = Partner
        fields = [
            # Primary Contact Information
            "primary_contact_first_name",
            "primary_contact_last_name",
            "primary_contact_phone_number",
            # Company Information
            "company_name",
            "company_phone",
            "company_email",
            "partner_type",
            "domain",
        ]
        widgets = {
            "primary_contact_first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "First Name",
                },
            ),
            "primary_contact_last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Last Name",
                },
            ),
            "primary_contact_phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "(555) 123-4567",
                    "type": "tel",
                },
            ),
            "company_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Company Name",
                },
            ),
            "company_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "(555) 987-6543",
                    "type": "tel",
                },
            ),
            "company_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "info@company.com",
                },
            ),
            "partner_type": forms.Select(
                attrs={
                    "class": "form-control",
                },
            ),
            "domain": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "example.com",
                },
            ),
        }
        labels = {
            "primary_contact_first_name": "First Name",
            "primary_contact_last_name": "Last Name",
            "primary_contact_phone_number": "Phone Number",
            "company_name": "Company Name",
            "company_phone": "Company Phone",
            "company_email": "Company Email",
            "partner_type": "Partner Type",
            "domain": "Domian",
        }
        help_texts = {
            "primary_contact_phone_number": "Your direct contact number",
            "company_phone": "Main company phone number",
            "company_email": "General company email address",
            "partner_type": "Select the type of partner organization",
            "domain": "The organization's domain",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make certain fields required
        self.fields["primary_contact_first_name"].required = True
        self.fields["primary_contact_last_name"].required = True
        self.fields["company_name"].required = True
        self.fields["partner_type"].required = True

        # Optional fields
        self.fields["primary_contact_phone_number"].required = False
        self.fields["company_phone"].required = False
        self.fields["company_email"].required = False
        self.fields["domain"].required = False

    def clean_primary_contact_phone_number(self):
        """Validate and format phone number"""
        phone = self.cleaned_data.get("primary_contact_phone_number")
        if phone:
            # Remove common formatting characters
            cleaned = "".join(filter(str.isdigit, phone))
            if len(cleaned) < phone_number_digits:
                msg = "Phone number must be at least 10 digits"
                raise ValidationError(msg)
        return phone

    def clean_company_phone(self):
        """Validate and format company phone number"""
        phone = self.cleaned_data.get("company_phone")
        if phone:
            # Remove common formatting characters
            cleaned = "".join(filter(str.isdigit, phone))
            if len(cleaned) < phone_number_digits:
                msg = "Phone number must be at least 10 digits"
                raise ValidationError(msg)
        return phone

    def save(self, commit=True):
        """
        Override save to handle any post-save operations.
        Note: HubSpot sync should be handled by signals or view logic.
        """
        instance = super().save(commit=False)

        if commit:
            instance.save()
            # The updated_at field will automatically be set
            # This will trigger needs_hubspot_sync to return True

        return instance
