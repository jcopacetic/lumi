# lumi/partners/signals.py
import logging
import threading

from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver

from lumi.partners.models import Partner
from lumi.partners.tasks import sync_full_partner_to_hubspot
from lumi.partners.tasks import sync_partner_company_to_hubspot
from lumi.partners.tasks import sync_partner_contact_to_hubspot

logger = logging.getLogger(__name__)


# Thread-local storage for tracking changes
_thread_locals = threading.local()

# Define which fields belong to contact vs company
CONTACT_FIELDS = {
    "email",
    "primary_contact_first_name",
    "primary_contact_last_name",
    "primary_contact_phone_number",
    "partner_type",
    "is_active",
}

COMPANY_FIELDS = {
    "company_name",
    "company_phone",
    "company_email",
    "partner_type",
    "is_active",
}


@receiver(pre_save, sender=Partner)
def backup_partner_data(sender, instance, **kwargs):
    """Store original values before save"""
    if instance.pk:  # Only for updates, not new instances
        try:
            original = Partner.objects.get(pk=instance.pk)
            _thread_locals.partner_backup = {
                "email": original.email,
                "primary_contact_first_name": original.primary_contact_first_name,
                "primary_contact_last_name": original.primary_contact_last_name,
                "primary_contact_phone_number": original.primary_contact_phone_number,
                "company_name": original.company_name,
                "company_phone": original.company_phone,
                "company_email": original.company_email,
                "partner_type": original.partner_type,
                "is_active": original.is_active,
            }
        except Partner.DoesNotExist:
            _thread_locals.partner_backup = None
    else:
        _thread_locals.partner_backup = None


@receiver(post_save, sender=Partner)
def sync_partner_to_hubspot_on_change(sender, instance, created, **kwargs):
    """
    Trigger HubSpot sync based on what changed.

    Strategy:
    - New partner: Full sync (contact + company + association)
    - Contact fields changed: Sync contact only
    - Company fields changed: Sync company only
    - Both changed: Full sync
    """
    # Skip if this save was triggered by mark_synced_to_hubspot
    # (to avoid infinite loop)
    update_fields = kwargs.get("update_fields")
    if update_fields and "last_synced_to_hubspot" in update_fields:
        logger.debug(
            "Skipping HubSpot sync for %s (sync timestamp update)",
            instance.email,
        )
        return

    if created:
        # New partner created - do full sync
        logger.info(
            "New partner created: %s. Triggering full HubSpot sync.",
            instance.email,
        )
        sync_full_partner_to_hubspot.delay(instance.id)
        return

    # Check what changed for existing partners
    backup = getattr(_thread_locals, "partner_backup", None)

    if not backup:
        # No backup means we can't detect changes, do full sync to be safe
        logger.warning(
            "No backup found for partner %s. \
                Triggering full sync as precaution.",
            instance.email,
        )
        sync_full_partner_to_hubspot.delay(instance.id)
        _thread_locals.partner_backup = None
        return

    # Detect which fields changed
    changed_fields = []
    contact_changed = False
    company_changed = False

    fields_to_check = [
        "email",
        "primary_contact_first_name",
        "primary_contact_last_name",
        "primary_contact_phone_number",
        "company_name",
        "company_phone",
        "company_email",
        "partner_type",
        "is_active",
    ]

    for field in fields_to_check:
        old_value = backup.get(field)
        new_value = getattr(instance, field)

        if old_value != new_value:
            changed_fields.append(
                {
                    "field": field,
                    "old": old_value,
                    "new": new_value,
                },
            )

            # Track whether contact or company info changed
            if field in CONTACT_FIELDS:
                contact_changed = True
            if field in COMPANY_FIELDS:
                company_changed = True

    # Clean up thread-local storage
    _thread_locals.partner_backup = None

    # If nothing changed, don't sync
    if not changed_fields:
        logger.debug(
            "No changes detected for partner %s. Skipping sync.",
            instance.email,
        )
        return

    # Log what changed
    field_names = [change["field"] for change in changed_fields]
    logger.info(
        "Partner %s updated. Changed fields: %s",
        instance.email,
        field_names,
    )

    # Trigger appropriate sync task(s) based on what changed
    if contact_changed and company_changed:
        # Both changed - do full sync for efficiency
        logger.info(
            "Both contact and company fields changed for %s. \
                Triggering full sync.",
            instance.email,
        )
        sync_full_partner_to_hubspot.delay(instance.id)

    elif contact_changed:
        # Only contact info changed
        logger.info(
            "Contact fields changed for %s. Triggering contact sync.",
            instance.email,
        )
        sync_partner_contact_to_hubspot.delay(instance.id)

    elif company_changed:
        # Only company info changed
        logger.info(
            "Company fields changed for %s. Triggering company sync.",
            instance.email,
        )
        sync_partner_company_to_hubspot.delay(instance.id)
