from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

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
    )
    partner_type = models.CharField(max_length=50, choices=PARTNER_TYPE_CHOICES)
    company_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Partner")
        verbose_name_plural = _("Partners")

    def __str__(self):
        return f"{self.company_name} ({self.get_partner_type_display()})"
