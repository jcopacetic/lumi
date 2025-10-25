import uuid

from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from lumi.partners.models import Partner

User = get_user_model()


class LoanType(models.Model):
    """Defines available loan types and which partners can access them"""

    MARKETING = "marketing"
    RENOVATION = "renovation"
    DEPOSIT = "deposit"

    LOAN_TYPE_CHOICES = [
        (MARKETING, "Marketing Loan"),
        (RENOVATION, "Renovation Loan"),
        (DEPOSIT, "Deposit Loan"),
    ]

    code = models.CharField(max_length=50, choices=LOAN_TYPE_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    allowed_partner_types = models.JSONField(
        default=list,
        help_text="List of partner types that can offer this loan type",
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order in dashboard")

    class Meta:
        verbose_name = _("Loan Type")
        verbose_name_plural = _("Loan Types")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def is_available_for_partner(self, partner):
        """Check if this loan type is available for a given partner"""
        if not self.allowed_partner_types:
            return True  # If empty, available to all
        return partner.partner_type in self.allowed_partner_types


class BaseLoanApplication(models.Model):
    """Abstract base model for all loan applications"""

    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_WITHDRAWN = "withdrawn"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    ]

    # NZ phone number validator
    nz_phone_validator = RegexValidator(
        regex=r"^(\+64|0)[2-9]\d{7,9}$",
        message="Enter a valid NZ phone number (e.g., 021234567 or +64212345678)",
    )

    # Unique identifier for retrieval
    application_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Partner attribution
    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name="%(class)s_applications",
    )

    # Customer identification fields for retrieval
    customer_email = models.EmailField(validators=[EmailValidator()])
    customer_date_of_birth = models.DateField()

    # Customer information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(
        max_length=20,
        validators=[nz_phone_validator],
        help_text="NZ phone number (e.g., 021234567 or +64212345678)",
    )

    # NZ address information
    street_address = models.CharField(max_length=255)
    suburb = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    postcode = models.CharField(
        max_length=4,
        validators=[
            RegexValidator(
                regex=r"^\d{4}$",
                message="Enter a valid 4-digit NZ postcode",
            ),
        ],
        help_text="4-digit postcode",
    )
    region = models.CharField(
        max_length=50,
        choices=[
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
        help_text="NZ region",
    )

    # Financial information (NZD)
    annual_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Annual income in NZD",
    )
    employment_status = models.CharField(
        max_length=50,
        choices=[
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
    )
    employer_name = models.CharField(max_length=255, blank=True)

    # IRD number (optional but common in NZ lending)
    ird_number = models.CharField(
        max_length=11,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\d{8,9}$",
                message="Enter a valid IRD number (8-9 digits)",
            ),
        ],
        help_text="IRD number (8-9 digits, optional)",
    )

    # Loan details (NZD)
    loan_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Loan amount in NZD",
    )
    loan_purpose = models.TextField()

    # Application management
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Notes and internal tracking
    internal_notes = models.TextField(blank=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["customer_email", "customer_date_of_birth"]),
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.application_id} - {self.first_name} {self.last_name}"

    @classmethod
    def find_application(cls, email, date_of_birth):
        """
        Helper method to retrieve applications by email and DOB
        Returns queryset of matching applications
        """
        return cls.objects.filter(
            customer_email__iexact=email,
            customer_date_of_birth=date_of_birth,
        ).order_by("-updated_at")


class MarketingLoanApplication(BaseLoanApplication):
    """Marketing loans for business promotional activities"""

    # Marketing-specific fields
    business_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=100)
    years_in_business = models.IntegerField()

    # NZBN (New Zealand Business Number)
    nzbn = models.CharField(
        max_length=13,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\d{13}$",
                message="Enter a valid NZBN (13 digits)",
            ),
        ],
        help_text="New Zealand Business Number (13 digits, optional)",
    )

    marketing_campaign_description = models.TextField()
    expected_roi = models.TextField(help_text="Expected return on investment")
    target_audience = models.TextField()

    # Marketing channels (NZD)
    digital_marketing_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Budget in NZD",
    )
    traditional_marketing_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Budget in NZD",
    )

    # GST registration
    gst_registered = models.BooleanField(
        default=False,
        help_text="Is the business GST registered?",
    )

    class Meta:
        verbose_name = _("Marketing Loan Application")
        verbose_name_plural = _("Marketing Loan Applications")
        ordering = ["-created_at"]


class RenovationLoanApplication(BaseLoanApplication):
    """Renovation loans for property improvements"""

    # Property information (NZ address format)
    property_address = models.CharField(max_length=255)
    property_suburb = models.CharField(max_length=100)
    property_city = models.CharField(max_length=100)
    property_postcode = models.CharField(
        max_length=4,
        validators=[
            RegexValidator(
                regex=r"^\d{4}$",
                message="Enter a valid 4-digit NZ postcode",
            ),
        ],
    )
    property_region = models.CharField(
        max_length=50,
        choices=[
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
    )

    property_type = models.CharField(
        max_length=50,
        choices=[
            ("house", "House"),
            ("apartment", "Apartment"),
            ("unit", "Unit"),
            ("townhouse", "Townhouse"),
            ("lifestyle_block", "Lifestyle Block"),
            ("commercial", "Commercial"),
        ],
    )
    property_ownership = models.CharField(
        max_length=50,
        choices=[
            ("owned", "Owned (Freehold)"),
            ("mortgaged", "Mortgaged"),
        ],
    )

    # Renovation details (NZD)
    renovation_description = models.TextField()
    renovation_type = models.CharField(
        max_length=50,
        choices=[
            ("kitchen", "Kitchen"),
            ("bathroom", "Bathroom"),
            ("extension", "Extension"),
            ("weathertightness", "Weathertightness/Re-cladding"),
            ("insulation", "Insulation"),
            ("earthquake_strengthening", "Earthquake Strengthening"),
            ("full_renovation", "Full Renovation"),
            ("other", "Other"),
        ],
    )

    estimated_property_value_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Value in NZD",
    )
    estimated_property_value_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Value in NZD",
    )

    # NZ building consent requirements
    building_consent_required = models.BooleanField(
        default=False,
        help_text="Does this renovation require a building consent?",
    )
    building_consent_obtained = models.BooleanField(default=False)

    contractor_quotes_obtained = models.BooleanField(default=False)
    contractor_name = models.CharField(max_length=255, blank=True)
    contractor_licensed = models.BooleanField(
        default=False,
        help_text="Is the contractor a Licensed Building Practitioner (LBP)?",
    )

    class Meta:
        verbose_name = _("Renovation Loan Application")
        verbose_name_plural = _("Renovation Loan Applications")
        ordering = ["-created_at"]


class DepositLoanApplication(BaseLoanApplication):
    """Deposit loans for property purchases (common in NZ market)"""

    # Property being purchased (NZ address format)
    property_address = models.CharField(max_length=255)
    property_suburb = models.CharField(max_length=100)
    property_city = models.CharField(max_length=100)
    property_postcode = models.CharField(
        max_length=4,
        validators=[
            RegexValidator(
                regex=r"^\d{4}$",
                message="Enter a valid 4-digit NZ postcode",
            ),
        ],
    )
    property_region = models.CharField(
        max_length=50,
        choices=[
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
    )

    property_type = models.CharField(
        max_length=50,
        choices=[
            ("house", "House"),
            ("apartment", "Apartment"),
            ("unit", "Unit"),
            ("townhouse", "Townhouse"),
            ("lifestyle_block", "Lifestyle Block"),
            ("section", "Section/Land"),
        ],
    )

    # Purchase details (NZD)
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Purchase price in NZD",
    )
    deposit_amount_required = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Deposit amount in NZD",
    )

    # First home buyer (relevant for NZ First Home schemes)
    is_first_home_buyer = models.BooleanField(default=False)
    first_home_grant_approved = models.BooleanField(
        default=False,
        help_text="Has First Home Grant been approved?",
    )
    first_home_loan_approved = models.BooleanField(
        default=False,
        help_text="Has First Home Loan been approved?",
    )

    property_identified = models.BooleanField(
        default=False,
        help_text="Has the customer identified the property they want to purchase?",
    )

    # Existing mortgage information (NZD)
    has_existing_mortgage = models.BooleanField(default=False)
    existing_mortgage_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Balance in NZD",
    )

    # KiwiSaver and other NZ-specific deposit sources
    kiwisaver_withdrawal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="KiwiSaver withdrawal amount in NZD",
    )
    other_deposit_sources = models.TextField(
        blank=True,
        help_text="Other sources: savings, family assistance, gifts, etc.",
    )

    # Pre-approval status
    mortgage_pre_approval = models.BooleanField(
        default=False,
        help_text="Has mortgage pre-approval been obtained?",
    )
    mortgage_pre_approval_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Pre-approved amount in NZD",
    )

    class Meta:
        verbose_name = _("Deposit Loan Application")
        verbose_name_plural = _("Deposit Loan Applications")
        ordering = ["-created_at"]


class ApplicationDocument(models.Model):
    """Supporting documents for loan applications"""

    DOCUMENT_TYPE_CHOICES = [
        ("id", "Identification (Driver Licence/Passport)"),
        ("income", "Income Proof (Payslips/Tax Returns)"),
        ("bank_statement", "Bank Statement"),
        ("ird_summary", "IRD Summary of Earnings"),
        ("quote", "Contractor Quote"),
        ("valuation", "Property Valuation"),
        ("building_consent", "Building Consent"),
        ("kiwisaver", "KiwiSaver Withdrawal Application"),
        ("first_home_grant", "First Home Grant Approval"),
        ("mortgage_preapproval", "Mortgage Pre-approval"),
        ("rates_notice", "Rates Notice"),
        ("title", "Property Title"),
        ("other", "Other"),
    ]

    # Generic foreign key reference
    application_id = models.UUIDField()
    application_type = models.CharField(max_length=50)  # Store model name

    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to="loan_applications/%Y/%m/%d/")
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
    )

    class Meta:
        verbose_name = _("Application Document")
        verbose_name_plural = _("Application Documents")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.filename} - {self.get_document_type_display()}"
