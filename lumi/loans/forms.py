from django import forms
from django.core.exceptions import ValidationError


class BaseApplicationForm(forms.Form):
    """Step 1: Customer Information and Basic Financial Details"""

    # Customer identification (for retrieval)
    customer_email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "customer@example.co.nz"},
        ),
    )
    customer_date_of_birth = forms.DateField(
        label="Date of Birth",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        help_text="Used to retrieve your application later",
    )

    # Customer information
    first_name = forms.CharField(
        label="First Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Last Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone_number = forms.CharField(
        label="Phone Number",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "021 234 5678 or +64 21 234 5678",
            },
        ),
        help_text="NZ mobile or landline number",
    )

    # Address information
    street_address = forms.CharField(
        label="Street Address",
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "123 Queen Street"},
        ),
    )
    suburb = forms.CharField(
        label="Suburb",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Auckland Central"},
        ),
    )
    city = forms.CharField(
        label="City/Town",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Auckland"},
        ),
    )
    postcode = forms.CharField(
        label="Postcode",
        max_length=4,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "1010"}),
        help_text="4-digit NZ postcode",
    )
    region = forms.ChoiceField(
        label="Region",
        choices=[
            ("", "Select region..."),
            ("northland", "Northland"),
            ("auckland", "Auckland"),
            ("waikato", "Waikato"),
            ("bay_of_plenty", "Bay of Plenty"),
            ("gisborne", "Gisborne"),
            ("hawkes_bay", "Hawke's Bay"),
            ("taranaki", "Taranaki"),
            ("manawatu_whanganui", "Manawatū-Whanganui"),
            ("wellington", "Wellington"),
            ("tasman", "Tasman"),
            ("nelson", "Nelson"),
            ("marlborough", "Marlborough"),
            ("west_coast", "West Coast"),
            ("canterbury", "Canterbury"),
            ("otago", "Otago"),
            ("southland", "Southland"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Financial information
    annual_income = forms.DecimalField(
        label="Annual Income (before tax)",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "75000.00"},
        ),
        help_text="Your gross annual income in NZD",
    )
    employment_status = forms.ChoiceField(
        label="Employment Status",
        choices=[
            ("", "Select..."),
            ("full_time", "Full Time"),
            ("part_time", "Part Time"),
            ("self_employed", "Self Employed"),
            ("contractor", "Contractor"),
            ("casual", "Casual"),
            ("retired", "Retired"),
            ("beneficiary", "Beneficiary"),
            ("student", "Student"),
            ("unemployed", "Unemployed"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    employer_name = forms.CharField(
        label="Employer Name",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Optional for self-employed, contractors, or retired",
    )

    # IRD Number (optional)
    ird_number = forms.CharField(
        label="IRD Number",
        max_length=11,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "123-456-789"},
        ),
        help_text="Optional: 8-9 digit IRD number",
    )

    # Loan details
    loan_amount = forms.DecimalField(
        label="Loan Amount Requested",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "50000.00"},
        ),
        help_text="Amount in NZD",
    )
    loan_purpose = forms.CharField(
        label="Purpose of Loan",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        help_text="Please describe how you intend to use this loan",
    )

    def clean_postcode(self):
        postcode = self.cleaned_data.get("postcode")
        if postcode and not postcode.isdigit():
            raise ValidationError("Postcode must contain only digits")  # noqa: TRY003 EM101
        if postcode and len(postcode) != 4:  # noqa: PLR2004
            raise ValidationError("NZ postcode must be exactly 4 digits")  # noqa: TRY003 EM101
        return postcode

    def clean_ird_number(self):
        ird = self.cleaned_data.get("ird_number")
        if ird:
            # Remove any formatting
            ird_clean = ird.replace("-", "").replace(" ", "")
            if not ird_clean.isdigit():
                raise ValidationError("IRD number must contain only digits")  # noqa: TRY003 EM101
            if len(ird_clean) not in [8, 9]:
                raise ValidationError("IRD number must be 8 or 9 digits")  # noqa: TRY003 EM101
            return ird_clean
        return ird


class MarketingApplicationForm(forms.Form):
    """Step 2: Marketing Loan Specific Details"""

    business_name = forms.CharField(
        label="Business Name",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    business_type = forms.CharField(
        label="Type of Business",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., Retail, Hospitality, Professional Services",
            },
        ),
    )
    years_in_business = forms.IntegerField(
        label="Years in Business",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    # NZBN
    nzbn = forms.CharField(
        label="NZBN (New Zealand Business Number)",
        max_length=13,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "9429000000000"},
        ),
        help_text="Optional: 13-digit NZBN if registered",
    )

    # GST Registration
    gst_registered = forms.BooleanField(
        label="Is your business GST registered?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    marketing_campaign_description = forms.CharField(
        label="Marketing Campaign Description",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        help_text="Describe your planned marketing campaign in detail",
    )
    expected_roi = forms.CharField(
        label="Expected Return on Investment",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        help_text="What results do you expect from this marketing investment?",
    )
    target_audience = forms.CharField(
        label="Target Audience",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        help_text="Describe your target market and audience",
    )

    digital_marketing_budget = forms.DecimalField(
        label="Digital Marketing Budget",
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "0.00"},
        ),
        help_text="Social media, Google Ads, email marketing, etc. (NZD)",
    )
    traditional_marketing_budget = forms.DecimalField(
        label="Traditional Marketing Budget",
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "0.00"},
        ),
        help_text="Print, radio, TV, billboards, etc. (NZD)",
    )

    def clean_nzbn(self):
        nzbn = self.cleaned_data.get("nzbn")
        if nzbn:
            nzbn_clean = nzbn.replace(" ", "").replace("-", "")
            if not nzbn_clean.isdigit():
                raise ValidationError("NZBN must contain only digits")  # noqa: TRY003 EM101
            if len(nzbn_clean) != 13:  # noqa: PLR2004
                raise ValidationError("NZBN must be exactly 13 digits")  # noqa: TRY003 EM101
            return nzbn_clean
        return nzbn


class RenovationApplicationForm(forms.Form):
    """Step 2: Renovation Loan Specific Details"""

    # Property information
    property_address = forms.CharField(
        label="Property Address",
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "456 Main Road"},
        ),
    )
    property_suburb = forms.CharField(
        label="Suburb",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    property_city = forms.CharField(
        label="City/Town",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    property_postcode = forms.CharField(
        label="Postcode",
        max_length=4,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "1010"}),
        help_text="4-digit NZ postcode",
    )
    property_region = forms.ChoiceField(
        label="Region",
        choices=[
            ("", "Select region..."),
            ("northland", "Northland"),
            ("auckland", "Auckland"),
            ("waikato", "Waikato"),
            ("bay_of_plenty", "Bay of Plenty"),
            ("gisborne", "Gisborne"),
            ("hawkes_bay", "Hawke's Bay"),
            ("taranaki", "Taranaki"),
            ("manawatu_whanganui", "Manawatū-Whanganui"),
            ("wellington", "Wellington"),
            ("tasman", "Tasman"),
            ("nelson", "Nelson"),
            ("marlborough", "Marlborough"),
            ("west_coast", "West Coast"),
            ("canterbury", "Canterbury"),
            ("otago", "Otago"),
            ("southland", "Southland"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    property_type = forms.ChoiceField(
        label="Property Type",
        choices=[
            ("", "Select..."),
            ("house", "House"),
            ("apartment", "Apartment"),
            ("unit", "Unit"),
            ("townhouse", "Townhouse"),
            ("lifestyle_block", "Lifestyle Block"),
            ("commercial", "Commercial"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    property_ownership = forms.ChoiceField(
        label="Property Ownership",
        choices=[
            ("", "Select..."),
            ("owned", "Owned (Freehold)"),
            ("mortgaged", "Mortgaged"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Renovation details
    renovation_description = forms.CharField(
        label="Renovation Description",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        help_text="Describe the renovation work you plan to undertake",
    )
    renovation_type = forms.ChoiceField(
        label="Primary Renovation Type",
        choices=[
            ("", "Select..."),
            ("kitchen", "Kitchen"),
            ("bathroom", "Bathroom"),
            ("extension", "Extension"),
            ("weathertightness", "Weathertightness/Re-cladding"),
            ("insulation", "Insulation"),
            ("earthquake_strengthening", "Earthquake Strengthening"),
            ("full_renovation", "Full Renovation"),
            ("other", "Other"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    estimated_property_value_before = forms.DecimalField(
        label="Estimated Property Value Before Renovation",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "650000.00"},
        ),
        help_text="Current estimated value in NZD",
    )
    estimated_property_value_after = forms.DecimalField(
        label="Estimated Property Value After Renovation",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "750000.00"},
        ),
        help_text="Expected value after renovation in NZD",
    )

    # Building consent
    building_consent_required = forms.BooleanField(
        label="Does this renovation require a building consent?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Check with your local council if unsure",
    )
    building_consent_obtained = forms.BooleanField(
        label="Have you obtained building consent?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    # Contractor information
    contractor_quotes_obtained = forms.BooleanField(
        label="Have you obtained contractor quotes?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    contractor_name = forms.CharField(
        label="Contractor Name",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="If you have selected a contractor",
    )
    contractor_licensed = forms.BooleanField(
        label="Is the contractor a Licensed Building Practitioner (LBP)?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="LBP registration is required for certain building work",
    )

    def clean_property_postcode(self):
        postcode = self.cleaned_data.get("property_postcode")
        if postcode and not postcode.isdigit():
            raise ValidationError("Postcode must contain only digits")  # noqa: TRY003 EM101
        if postcode and len(postcode) != 4:  # noqa: PLR2004
            raise ValidationError("NZ postcode must be exactly 4 digits")  # noqa: TRY003 EM101
        return postcode


class DepositApplicationForm(forms.Form):
    """Step 2: Deposit Loan Specific Details"""

    # Property being purchased
    property_address = forms.CharField(
        label="Property Address",
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "789 Hill Street"},
        ),
        help_text="Leave blank if property not yet identified",
    )
    property_suburb = forms.CharField(
        label="Suburb",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    property_city = forms.CharField(
        label="City/Town",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Wellington"},
        ),
    )
    property_postcode = forms.CharField(
        label="Postcode",
        max_length=4,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "6011"}),
        help_text="4-digit NZ postcode",
    )
    property_region = forms.ChoiceField(
        label="Region",
        choices=[
            ("", "Select region..."),
            ("northland", "Northland"),
            ("auckland", "Auckland"),
            ("waikato", "Waikato"),
            ("bay_of_plenty", "Bay of Plenty"),
            ("gisborne", "Gisborne"),
            ("hawkes_bay", "Hawke's Bay"),
            ("taranaki", "Taranaki"),
            ("manawatu_whanganui", "Manawatū-Whanganui"),
            ("wellington", "Wellington"),
            ("tasman", "Tasman"),
            ("nelson", "Nelson"),
            ("marlborough", "Marlborough"),
            ("west_coast", "West Coast"),
            ("canterbury", "Canterbury"),
            ("otago", "Otago"),
            ("southland", "Southland"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    property_type = forms.ChoiceField(
        label="Property Type",
        choices=[
            ("", "Select..."),
            ("house", "House"),
            ("apartment", "Apartment"),
            ("unit", "Unit"),
            ("townhouse", "Townhouse"),
            ("lifestyle_block", "Lifestyle Block"),
            ("section", "Section/Land"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    purchase_price = forms.DecimalField(
        label="Purchase Price",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "850000.00"},
        ),
        help_text="Expected purchase price in NZD",
    )
    deposit_amount_required = forms.DecimalField(
        label="Deposit Amount Required",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "170000.00"},
        ),
        help_text="Typically 20% of purchase price (NZD)",
    )

    # Purchase details
    is_first_home_buyer = forms.BooleanField(
        label="Are you a first home buyer?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Buying your first home in New Zealand",
    )

    # First Home schemes
    first_home_grant_approved = forms.BooleanField(
        label="Have you been approved for a First Home Grant?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Kāinga Ora First Home Grant",
    )
    first_home_loan_approved = forms.BooleanField(
        label="Have you been approved for a First Home Loan?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Kāinga Ora First Home Loan (low deposit)",
    )

    property_identified = forms.BooleanField(
        label="Have you identified the property you want to purchase?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    # Existing mortgage information
    has_existing_mortgage = forms.BooleanField(
        label="Do you have an existing mortgage?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    existing_mortgage_balance = forms.DecimalField(
        label="Existing Mortgage Balance",
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "0.00"},
        ),
        help_text="Current balance in NZD",
    )

    # Mortgage pre-approval
    mortgage_pre_approval = forms.BooleanField(
        label="Have you obtained mortgage pre-approval?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    mortgage_pre_approval_amount = forms.DecimalField(
        label="Mortgage Pre-approval Amount",
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "0.00"},
        ),
        help_text="Pre-approved amount in NZD",
    )

    # KiwiSaver withdrawal
    kiwisaver_withdrawal_amount = forms.DecimalField(
        label="KiwiSaver Withdrawal Amount",
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "0.00"},
        ),
        help_text="Amount you plan to withdraw from KiwiSaver (NZD)",
    )

    # Additional deposit sources
    other_deposit_sources = forms.CharField(
        label="Other Deposit Sources",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        help_text="e.g., Savings, family assistance, gifts, HomeStart Grant",
    )

    def clean_property_postcode(self):
        postcode = self.cleaned_data.get("property_postcode")
        if postcode:
            if not postcode.isdigit():
                raise ValidationError("Postcode must contain only digits")  # noqa: TRY003 EM101
            if len(postcode) != 4:  # noqa: PLR2004
                raise ValidationError("NZ postcode must be exactly 4 digits")  # noqa: TRY003 EM101
        return postcode


class ApplicationRetrievalForm(forms.Form):
    """Form to retrieve an existing draft application"""

    customer_email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "customer@example.co.nz"},
        ),
    )
    customer_date_of_birth = forms.DateField(
        label="Date of Birth",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        help_text="Enter the date of birth used when creating your application",
    )
