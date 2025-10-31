import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# HubSpot Object Type IDs
CONTACT_OBJECT_ID = "0-1"
COMPANY_OBJECT_ID = "0-2"

STATUS_CODE_204 = 204

# Association Type ID for Contact to Company
CONTACT_TO_COMPANY_ASSOCIATION_TYPE = 1  # Primary company association


class HubSpotAPIError(Exception):
    """Custom exception for HubSpot API errors"""


class HubSpotClient:
    """Client for interacting with HubSpot CRM API v3"""

    BASE_URL = "https://api.hubapi.com"

    def __init__(self, api_key: str | None = None):
        """
        Initialize HubSpot client

        Args:
            api_key: HubSpot private app access token
            (falls back to settings.HUBSPOT_API_KEY)
        """
        self.api_key = api_key or getattr(settings, "HUBSPOT_ACCESS_TOKEN", None)
        if not self.api_key:
            msg = "HubSpot API key is required"
            raise ValueError(msg)

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make HTTP request to HubSpot API

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            HubSpotAPIError: If request fails
        """
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30,
            )

            # Log request details
            logger.debug(
                "HubSpot API %s %s - Status: %s",
                method,
                endpoint,
                response.status_code,
            )

            response.raise_for_status()

            # Some endpoints return 204 No Content
            if response.status_code == STATUS_CODE_204:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            error_msg = f"HubSpot API error: {e}"
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"HubSpot API error: {error_detail}"
                except ValueError:
                    error_msg = f"HubSpot API error: {e.response.text}"

            logger.exception(error_msg)
            raise HubSpotAPIError(error_msg) from e

        except requests.exceptions.RequestException as e:
            error_msg = "HubSpot request failed"
            logger.exception(error_msg)
            raise HubSpotAPIError(error_msg) from e

    def create_or_update_contact_by_email(
        self,
        email: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create or update a contact using email as unique identifier

        Args:
            email: Contact's email address (unique identifier)
            properties: Dictionary of HubSpot contact properties to set
                       Common properties: firstname, lastname, phone, company, etc.

        Returns:
            Contact data including HubSpot contact ID

        Example:
            client.create_or_update_contact_by_email(
                email="john@example.com",
                properties={
                    "firstname": "John",
                    "lastname": "Doe",
                    "phone": "+1234567890",
                    "partner_type": "real_estate"
                }
            )
        """
        # Ensure email is in properties
        properties["email"] = email

        endpoint = "/crm/v3/objects/contacts"
        data = {
            "properties": properties,
        }

        try:
            # Try to create the contact
            response = self._make_request("POST", endpoint, data=data)
            logger.info(
                "Created HubSpot contact: %s (ID: %s)",
                email,
                response["id"],
            )

        except HubSpotAPIError as e:
            # If contact exists (409 conflict), update it instead
            if "409" in str(e) or "Contact already exists" in str(e):
                logger.info(
                    "Contact %s exists, updating instead",
                    email,
                )
                return self._update_contact_by_email(email, properties)
            raise
        else:
            return response

    def _update_contact_by_email(
        self,
        email: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update an existing contact by email

        Args:
            email: Contact's email address
            properties: Properties to update

        Returns:
            Updated contact data
        """
        endpoint = f"/crm/v3/objects/contacts/{email}"
        params = {"idProperty": "email"}
        data = {
            "properties": properties,
        }

        response = self._make_request("PATCH", endpoint, data=data, params=params)
        logger.info(
            "Updated HubSpot contact: %s (ID: %s)",
            email,
            response["id"],
        )
        return response

    def get_contact_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Retrieve a contact by email address

        Args:
            email: Contact's email address

        Returns:
            Contact data or None if not found
        """
        endpoint = f"/crm/v3/objects/contacts/{email}"
        params = {"idProperty": "email"}

        try:
            response = self._make_request("GET", endpoint, params=params)
        except HubSpotAPIError:
            logger.warning(
                "Contact not found: %s",
                email,
            )
            return None
        else:
            return response

    def create_or_update_company_by_domain(
        self,
        domain: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create or update a company using domain as unique identifier

        Args:
            domain: Company's website domain (unique identifier)
            properties: Dictionary of HubSpot company properties to set
                       Common properties: name, phone, city, state, industry, etc.

        Returns:
            Company data including HubSpot company ID

        Example:
            client.create_or_update_company_by_domain(
                domain="example.com",
                properties={
                    "name": "Example Corp",
                    "phone": "+1234567890",
                    "city": "San Francisco",
                    "type": "PARTNER"
                }
            )
        """
        # Ensure domain is in properties
        properties["domain"] = domain

        endpoint = "/crm/v3/objects/companies"
        data = {
            "properties": properties,
        }

        try:
            # Try to create the company
            response = self._make_request("POST", endpoint, data=data)
            logger.info(
                "Created HubSpot company: %s (ID: %s)",
                domain,
                response["id"],
            )

        except HubSpotAPIError as e:
            # If company exists (409 conflict), update it instead
            if "409" in str(e) or "Company already exists" in str(e):
                logger.info(
                    "Company %s exists, updating instead",
                    domain,
                )
                return self._update_company_by_domain(domain, properties)
            raise

        else:
            return response

    def _update_company_by_domain(
        self,
        domain: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update an existing company by domain

        Args:
            domain: Company's domain
            properties: Properties to update

        Returns:
            Updated company data
        """
        endpoint = f"/crm/v3/objects/companies/{domain}"
        params = {"idProperty": "domain"}
        data = {
            "properties": properties,
        }

        response = self._make_request("PATCH", endpoint, data=data, params=params)
        logger.info(
            "Updated HubSpot company: %s (ID: %s)",
            domain,
            response["id"],
        )
        return response

    def get_company_by_domain(self, domain: str) -> dict[str, Any] | None:
        """
        Retrieve a company by domain

        Args:
            domain: Company's website domain

        Returns:
            Company data or None if not found
        """
        endpoint = f"/crm/v3/objects/companies/{domain}"
        params = {"idProperty": "domain"}

        try:
            return self._make_request("GET", endpoint, params=params)

        except HubSpotAPIError:
            logger.warning(
                "Company not found: %s",
                domain,
            )
            return None

    def associate_contact_to_company(
        self,
        contact_id: str,
        company_id: str,
        association_type: int = CONTACT_TO_COMPANY_ASSOCIATION_TYPE,
    ) -> dict[str, Any]:
        """
        Create an association between a contact and a company

        Args:
            contact_id: HubSpot contact ID
            company_id: HubSpot company ID
            association_type: Type of association (default: 1 = primary company)

        Returns:
            Association response data

        Note:
            Common association types:
            - 1: Contact to Company (Primary)
            - 2: Contact to Company (Unlabeled)
        """
        endpoint = (
            f"/crm/v4/objects/contacts/{contact_id}/associations/companies/{company_id}"
        )

        data = [
            {
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": association_type,
            },
        ]

        response = self._make_request("PUT", endpoint, data=data)
        logger.info(
            "Associated contact %s to company %s (type: %s)",
            contact_id,
            company_id,
            association_type,
        )
        return response

    def remove_association(
        self,
        contact_id: str,
        company_id: str,
        association_type: int = CONTACT_TO_COMPANY_ASSOCIATION_TYPE,
    ) -> None:
        """
        Remove an association between a contact and a company

        Args:
            contact_id: HubSpot contact ID
            company_id: HubSpot company ID
            association_type: Type of association to remove
        """
        endpoint = (
            f"/crm/v4/objects/contacts/{contact_id}/associations/companies/{company_id}"
        )

        data = [
            {
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": association_type,
            },
        ]

        self._make_request("DELETE", endpoint, data=data)
        logger.info(
            "Removed association between contact %s and company %s",
            contact_id,
            company_id,
        )

    def get_contact_companies(self, contact_id: str) -> list[dict[str, Any]]:
        """
        Get all companies associated with a contact

        Args:
            contact_id: HubSpot contact ID

        Returns:
            List of associated companies
        """
        endpoint = f"/crm/v3/objects/contacts/{contact_id}/associations/companies"

        try:
            response = self._make_request("GET", endpoint)
            return response.get("results", [])
        except HubSpotAPIError:
            logger.warning(
                "No companies found for contact %s",
                contact_id,
            )
            return []

    def batch_update_contacts(
        self,
        updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Batch update multiple contacts

        Args:
            updates: List of contact update dicts, each containing:
                    - id: Contact ID
                    - properties: Dict of properties to update

        Returns:
            Batch operation results

        Example:
            client.batch_update_contacts([
                {"id": "123", "properties": {"firstname": "John"}},
                {"id": "456", "properties": {"lastname": "Doe"}}
            ])
        """
        endpoint = "/crm/v3/objects/contacts/batch/update"
        data = {"inputs": updates}

        response = self._make_request("POST", endpoint, data=data)
        logger.info(
            "Batch updated %s contacts",
            len(updates),
        )
        return response

    def batch_update_companies(
        self,
        updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Batch update multiple companies

        Args:
            updates: List of company update dicts, each containing:
                    - id: Company ID
                    - properties: Dict of properties to update

        Returns:
            Batch operation results
        """
        endpoint = "/crm/v3/objects/companies/batch/update"
        data = {"inputs": updates}

        response = self._make_request("POST", endpoint, data=data)
        logger.info(
            "Batch updated %s companies",
            len(updates),
        )
        return response


# Utility function for Partner model integration
def sync_partner_to_hubspot(partner) -> tuple[str, str]:
    """
    Sync a Partner instance to HubSpot

    Args:
        partner: Partner model instance

    Returns:
        Tuple of (contact_id, company_id)
    """
    client = HubSpotClient()

    # Prepare contact properties
    contact_properties = {
        "email": partner.email,
        "firstname": partner.primary_contact_first_name or "",
        "lastname": partner.primary_contact_last_name or "",
        "phone": partner.primary_contact_phone_number or "",
        "partner_type": partner.partner_type,
        "partner_status": partner.invite_status,
    }

    # Create/update contact
    contact_response = client.create_or_update_contact_by_email(
        email=partner.email,
        properties=contact_properties,
    )
    contact_id = contact_response["id"]

    # Prepare company properties
    # Extract domain from company email or use a default
    domain = None
    if partner.company_email:
        domain = partner.company_email.split("@")[-1]

    company_properties = {
        "name": partner.company_name,
        "phone": partner.company_phone or "",
        "partner_type": partner.partner_type,
    }

    if domain:
        company_properties["domain"] = domain
        # Create/update company
        company_response = client.create_or_update_company_by_domain(
            domain=domain,
            properties=company_properties,
        )
        company_id = company_response["id"]

        # Associate contact to company
        client.associate_contact_to_company(contact_id, company_id)
    else:
        # If no domain, create company without domain identifier
        # This requires using the company ID endpoint instead
        company_id = None
        logger.warning(
            "No domain available for company %s, skipping company sync",
            partner.company_name,
        )

    # Update partner with HubSpot IDs
    partner.mark_synced_to_hubspot(
        contact_id=contact_id,
        company_id=company_id,
    )

    return contact_id, company_id
