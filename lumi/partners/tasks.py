# lumi/hubspot/tasks.py
import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.db import models
from django.db import transaction

from lumi.hubspot.client import HubSpotAPIError
from lumi.hubspot.client import HubSpotClient
from lumi.partners.models import Partner

logger = logging.getLogger(__name__)


def get_hubspot_client() -> HubSpotClient:
    """
    Get initialized HubSpot client with validation.

    Returns:
        Initialized HubSpotClient

    Raises:
        ValueError: If API key not configured
        HubSpotAPIError: If client initialization fails
    """
    access_token = getattr(settings, "HUBSPOT_ACCESS_TOKEN", None)
    if not access_token:
        msg = "HUBSPOT_ACCESS_TOKEN not configured in settings"
        raise ValueError(msg)

    try:
        return HubSpotClient(api_key=access_token)
    except Exception:
        logger.exception("Failed to initialize HubSpot client")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(HubSpotAPIError,),
)
def sync_partner_contact_to_hubspot(self, partner_id: int) -> dict[str, Any]:
    """Sync only partner's contact information to HubSpot."""

    try:
        partner = Partner.objects.get(id=partner_id)
    except Partner.DoesNotExist:
        logger.exception("Partner %s not found", partner_id)
        return {"success": False, "error": "Partner not found"}

    try:
        # Get validated client
        hs_client = get_hubspot_client()

        # Prepare contact properties
        contact_properties = {
            "email": partner.email,
            "firstname": partner.primary_contact_first_name or "",
            "lastname": partner.primary_contact_last_name or "",
            "phone": partner.primary_contact_phone_number or "",
            "partner_type": partner.get_partner_type_display(),
            "company": partner.company_name,
        }

        if partner.has_accepted and partner.accepted_at:
            contact_properties["partner_accepted_at"] = partner.accepted_at.isoformat()

        contact_response = hs_client.create_or_update_contact_by_email(
            email=partner.email,
            properties=contact_properties,
        )

        contact_id = contact_response["id"]

        with transaction.atomic():
            partner.hubspot_contact_id = contact_id
            partner.last_synced_to_hubspot = partner.updated_at
            partner.save(update_fields=["hubspot_contact_id", "last_synced_to_hubspot"])

        logger.info(
            "Successfully synced contact for %s to HubSpot (contact_id: %s)",
            partner.email,
            contact_id,
        )

    except ValueError as e:
        # Configuration error - don't retry
        error_msg = f"HubSpot configuration error: {e}"
        logger.exception(error_msg)
        return {"success": False, "error": error_msg}

    except HubSpotAPIError:
        # API error - will auto-retry
        logger.exception(
            "HubSpot API error syncing contact for partner %s",
            partner_id,
        )
        raise

    except Exception as e:
        logger.exception(
            "Unexpected error syncing contact for partner %s",
            partner_id,
        )
        return {"success": False, "error": str(e), "partner_id": partner_id}

    else:
        return {
            "success": True,
            "partner_id": partner_id,
            "contact_id": contact_id,
            "email": partner.email,
        }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(HubSpotAPIError,),
)
def sync_partner_company_to_hubspot(self, partner_id: int) -> dict[str, Any]:
    """
    Sync only partner's company information to HubSpot.
    Triggered when company fields change (name, phone, email, etc.)

    Args:
        partner_id: ID of the Partner to sync

    Returns:
        Dict with sync results
    """
    access_token = settings.HUBSPOT_ACCESS_TOKEN
    if not access_token:
        logger.exception("HUBSPOT_ACCESS_TOKEN not configured")
        return {"success": False, "error": "HubSpot API key not configured"}

    try:
        partner = Partner.objects.get(id=partner_id)
    except Partner.DoesNotExist:
        logger.exception("Partner %s not found", partner_id)
        return {"success": False, "error": "Partner not found"}

    # Extract domain from company email
    domain = None
    if partner.company_email:
        domain = partner.company_email.split("@")[-1]

    if not domain:
        logger.warning(
            "Partner %s (%s) has no company email/domain. Cannot sync company \
                to HubSpot.",
            partner_id,
            partner.email,
        )
        return {
            "success": False,
            "error": "No company domain available",
            "partner_id": partner_id,
        }

    try:
        hs_client = HubSpotClient(api_key=access_token)

        # Prepare company properties
        company_properties = {
            "name": partner.company_name,
            "domain": domain,
            "phone": partner.company_phone or "",
            "partner_type": partner.get_partner_type_display(),
            "type": "PARTNER",
        }

        # Create or update company by domain
        company_response = hs_client.create_or_update_company_by_domain(
            domain=domain,
            properties=company_properties,
        )

        company_id = company_response["id"]

        # Update partner with company ID
        with transaction.atomic():
            partner.hubspot_company_id = company_id
            partner.last_synced_to_hubspot = partner.updated_at
            partner.save(update_fields=["hubspot_company_id", "last_synced_to_hubspot"])

        # If we have both IDs, ensure they're associated
        if partner.hubspot_contact_id and company_id:
            try:
                hs_client.associate_contact_to_company(
                    contact_id=partner.hubspot_contact_id,
                    company_id=company_id,
                )
            except HubSpotAPIError:
                # Association might already exist, just log warning
                logger.warning(
                    "Could not associate contact %s to company %s",
                    partner.hubspot_contact_id,
                    company_id,
                )

        logger.info(
            "Successfully synced company for %s to HubSpot (company_id: %s, \
                domain: %s)",
            partner.email,
            company_id,
            domain,
        )

    except HubSpotAPIError:
        logger.exception(
            "HubSpot API error syncing company for partner %s",
            partner_id,
        )
        raise  # Celery will auto-retry

    except Exception as e:
        logger.exception(
            "Unexpected error syncing company for partner %s",
            partner_id,
        )
        return {"success": False, "error": str(e), "partner_id": partner_id}

    else:
        return {
            "success": True,
            "partner_id": partner_id,
            "company_id": company_id,
            "domain": domain,
        }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(HubSpotAPIError,),
)
def sync_full_partner_to_hubspot(self, partner_id: int) -> dict[str, Any]:
    """
    Sync both contact and company for a partner, then associate them.
    Triggered when partner is created or both contact/company fields change.

    Args:
        partner_id: ID of the Partner to sync

    Returns:
        Dict with complete sync results
    """
    access_token = settings.HUBSPOT_ACCESS_TOKEN
    if not access_token:
        logger.exception("HUBSPOT_ACCESS_TOKEN not configured")
        return {"success": False, "error": "HubSpot API key not configured"}

    try:
        partner = Partner.objects.get(id=partner_id)
    except Partner.DoesNotExist:
        logger.exception("Partner %s not found", partner_id)
        return {"success": False, "error": "Partner not found"}

    try:
        hs_client = HubSpotClient(api_key=access_token)

        # Step 1: Sync contact
        contact_properties = {
            "email": partner.email,
            "firstname": partner.primary_contact_first_name or "",
            "lastname": partner.primary_contact_last_name or "",
            "phone": partner.primary_contact_phone_number or "",
            "partner_type": partner.get_partner_type_display(),
            "company": partner.company_name,
        }

        if partner.has_accepted and partner.accepted_at:
            contact_properties["partner_accepted_at"] = partner.accepted_at.isoformat()

        contact_response = hs_client.create_or_update_contact_by_email(
            email=partner.email,
            properties=contact_properties,
        )
        contact_id = contact_response["id"]

        # Step 2: Sync company (if domain available)
        company_id = None
        domain = None

        if partner.company_email:
            domain = partner.company_email.split("@")[-1]

            company_properties = {
                "name": partner.company_name,
                "domain": domain,
                "phone": partner.company_phone or "",
                "partner_type": partner.get_partner_type_display(),
                "type": "PARTNER",
            }

            company_response = hs_client.create_or_update_company_by_domain(
                domain=domain,
                properties=company_properties,
            )
            company_id = company_response["id"]

            # Step 3: Associate contact to company
            try:
                hs_client.associate_contact_to_company(
                    contact_id=contact_id,
                    company_id=company_id,
                )
            except HubSpotAPIError as e:
                # Association might already exist, just log warning
                logger.warning(
                    "Could not associate contact %s to company %s: %s",
                    contact_id,
                    company_id,
                    e,
                )
        else:
            logger.info(
                "No company email for partner %s, skipping company sync",
                partner.email,
            )

        # Step 4: Update partner with HubSpot IDs
        with transaction.atomic():
            partner.hubspot_contact_id = contact_id
            partner.hubspot_company_id = company_id
            partner.last_synced_to_hubspot = partner.updated_at
            partner.save(
                update_fields=[
                    "hubspot_contact_id",
                    "hubspot_company_id",
                    "last_synced_to_hubspot",
                ],
            )

        logger.info(
            "Successfully synced partner %s to HubSpot (contact: %s, \
                company: %s)",
            partner.email,
            contact_id,
            company_id,
        )

    except HubSpotAPIError:
        logger.exception("HubSpot API error syncing partner %s", partner_id)
        raise  # Celery will auto-retry

    except Exception as e:
        logger.exception("Unexpected error syncing partner %s", partner_id)
        return {"success": False, "error": str(e), "partner_id": partner_id}

    else:
        return {
            "success": True,
            "partner_id": partner_id,
            "contact_id": contact_id,
            "company_id": company_id,
            "email": partner.email,
            "domain": domain,
        }


@shared_task()
def bulk_sync_all_partners(force: bool = False) -> dict[str, Any]:
    """
    Bulk sync multiple partners to HubSpot.
    Use this for initial data migration or manual re-sync.
    NOT triggered by signals - run manually via Django admin or management
    command.

    Args:
        force: If True, sync all partners. If False, only unsync partners.

    Returns:
        Summary of queued sync operations
    """
    access_token = settings.HUBSPOT_ACCESS_TOKEN
    if not access_token:
        return {"success": False, "error": "HubSpot API key not configured"}

    from django.db.models import Q

    if force:
        partners = Partner.objects.filter(is_active=True)
    else:
        # Only partners never synced or changed since last sync
        partners = Partner.objects.filter(is_active=True).filter(
            Q(last_synced_to_hubspot__isnull=True)
            | Q(updated_at__gt=models.F("last_synced_to_hubspot")),
        )

    total = partners.count()
    logger.info("Queueing %s partners for bulk HubSpot sync", total)

    queued = 0
    for partner in partners:
        try:
            sync_full_partner_to_hubspot.delay(partner.id)
            queued += 1
        except Exception:
            logger.exception("Failed to queue partner %s", partner.id)

    return {
        "success": True,
        "total_partners": total,
        "queued": queued,
        "message": f"Queued {queued}/{total} partners for sync",
    }
