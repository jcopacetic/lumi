import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()


class Partner(models.Model):
    """Vertical partners who use the tablets"""

    REAL_ESTATE = "real_estate"
    FAMILY_OFFICE = "family_office"
    MORTGAGE_BROKER = "mortgage_broker"

    PARTNER_TYPE_CHOICES = [
        (REAL_ESTATE, "Real Estate"),
        (FAMILY_OFFICE, "Family Office"),
        (MORTGAGE_BROKER, "Mortgage Broker"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="partner_profile",
        null=True,
        blank=True,
        help_text="User account (created after accepting invite)",
    )

    # Primary Contact Information (syncs to HubSpot Contact)
    email = models.EmailField(
        unique=True,
        help_text="Primary contact email - used as HubSpot contact identifier",
    )
    primary_contact_first_name = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name="First Name",
    )
    primary_contact_last_name = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name="Last Name",
    )
    primary_contact_phone_number = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name="Phone Number",
    )

    # Company Information (syncs to HubSpot Company)
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    company_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Company Phone",
    )
    company_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name="Company Email",
        help_text="General company email (may differ from primary contact)",
    )
    domain = models.URLField(max_length=180, null=True, blank=True)
    partner_type = models.CharField(
        max_length=50,
        choices=PARTNER_TYPE_CHOICES,
        verbose_name="Partner Type",
    )

    # Invitation Management
    invite_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique token for signup invitation",
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # HubSpot Integration Tracking
    hubspot_contact_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="HubSpot Contact ID for primary contact",
    )
    hubspot_company_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="HubSpot Company ID",
    )
    last_synced_to_hubspot = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this partner was synced to HubSpot",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Partner")
        verbose_name_plural = _("Partners")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["hubspot_contact_id"]),
            models.Index(fields=["hubspot_company_id"]),
        ]

    def __str__(self):
        return f"{self.company_name} ({self.get_partner_type_display()})"

    @property
    def primary_contact_full_name(self):
        """Get the full name of the primary contact"""
        parts = [self.primary_contact_first_name, self.primary_contact_last_name]
        return " ".join(filter(None, parts)) or "N/A"

    def send_invite(self):
        """Send invitation email to partner"""
        signup_url = self.get_invite_url()
        subject = "You're invited to join the Loan Portal"

        try:
            message = render_to_string(
                "emails/partner_invite.txt",
                {
                    "signup_url": signup_url,
                    "partner": self,
                    "company_name": self.company_name,
                },
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                fail_silently=False,
            )

            logger.info(
                f"Invite sent to partner {self.email} "  # noqa: G004
                f"(token={self.invite_token}, company={self.company_name})",
            )

        except Exception as e:
            logger.error(  # noqa: TRY400
                f"Failed to send invite to {self.email} "  # noqa: G004
                f"(company={self.company_name}): {e}",
            )
            raise

    def get_invite_url(self):
        """
        Generate the full signup URL with invite token
        Uses the partners:partner_signup URL pattern
        """
        path = reverse("partners:partner_signup", kwargs={"token": self.invite_token})
        return f"{settings.SITE_URL}{path}"

    def regenerate_invite_token(self, save=True):
        """Generate a new invite token (useful for re-invitations)"""
        self.invite_token = uuid.uuid4()
        self.invited_at = timezone.now()
        if save:
            self.save(update_fields=["invite_token", "invited_at"])
        logger.info("Regenerated invite token for partner %s", self.email)

    def is_invite_expired(self, expiry_days=7):
        """Check if the invite has expired"""
        if not self.invited_at:
            return True
        expiry_date = self.invited_at + timedelta(days=expiry_days)
        return timezone.now() > expiry_date

    def mark_as_accepted(self, user):
        """Mark invite as accepted and link to user account"""
        self.user = user
        self.accepted_at = timezone.now()
        self.save(update_fields=["user", "accepted_at"])
        logger.info(
            "Partner %s accepted invite and linked to user %s",
            self.email,
            user.id,
        )

    @property
    def has_accepted(self):
        """Check if partner has accepted the invite"""
        return self.accepted_at is not None and self.user is not None

    @property
    def invite_status(self):
        """Human-readable invite status"""
        if self.has_accepted:
            return "Accepted"
        if self.is_invite_expired():
            return "Expired"
        return "Pending"

    @property
    def needs_hubspot_sync(self):
        """Check if partner data has changed since last HubSpot sync"""
        if not self.last_synced_to_hubspot:
            return True
        return self.updated_at > self.last_synced_to_hubspot

    def mark_synced_to_hubspot(self, contact_id=None, company_id=None):
        """Update HubSpot sync timestamp and IDs"""
        if contact_id:
            self.hubspot_contact_id = contact_id
        if company_id:
            self.hubspot_company_id = company_id
        self.last_synced_to_hubspot = timezone.now()
        self.save(
            update_fields=[
                "hubspot_contact_id",
                "hubspot_company_id",
                "last_synced_to_hubspot",
            ],
        )
        logger.info(
            "Partner %s marked as synced to HubSpot (contact: %s, company: %s)",
            self.email,
            contact_id,
            company_id,
        )
