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
    email = models.EmailField(unique=True)
    invite_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique token for signup invitation",
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    partner_type = models.CharField(max_length=50, choices=PARTNER_TYPE_CHOICES)
    company_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Partner")
        verbose_name_plural = _("Partners")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} ({self.get_partner_type_display()})"

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

    def regenerate_invite_token(self, save=True):  # noqa: FBT002
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
