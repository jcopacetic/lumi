"""
Shared fixtures and configuration for partners app tests.

This file is automatically discovered by pytest and makes fixtures
available to all test files in the partners/tests directory.
"""

import pytest
from django.test import RequestFactory

from lumi.partners.models import Partner
from lumi.users.models import User


# Configure pytest-django
@pytest.fixture(autouse=True)
def _enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""


@pytest.fixture
def rf():
    """Provide RequestFactory instance."""
    return RequestFactory()


@pytest.fixture
def user(db):
    """Create a regular user."""
    return User.objects.create_user(
        email="testuser@example.com",
        password="testpass123",  # noqa: S106
    )


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    return User.objects.create_user(
        email="staff@example.com",
        password="testpass123",  # noqa: S106
        is_staff=True,
    )


@pytest.fixture
def partner(db):
    """Create a partner without a user."""
    return Partner.objects.create(
        email="partner@example.com",
        company_name="Test Company",
        partner_type=Partner.REAL_ESTATE,
        is_active=True,
    )


@pytest.fixture
def partner_with_user(db, user):
    """Create a partner linked to a user."""
    partner = Partner.objects.create(
        email=user.email,
        company_name="Test Company",
        partner_type=Partner.REAL_ESTATE,
        is_active=True,
        user=user,
    )
    partner.mark_as_accepted(user)
    return partner


@pytest.fixture
def partner_inactive(db, user):
    """Create an inactive partner linked to a user."""
    return Partner.objects.create(
        email=user.email,
        company_name="Inactive Company",
        partner_type=Partner.FAMILY_OFFICE,
        is_active=False,
        user=user,
    )


@pytest.fixture
def partner_expired(db):
    """Create a partner with expired invite."""
    from datetime import timedelta

    from django.utils import timezone

    partner = Partner.objects.create(
        email="expired@example.com",
        company_name="Expired Company",
        partner_type=Partner.MORTGAGE_BROKER,
        is_active=True,
    )
    # Set invited_at to 8 days ago (assuming 7 day expiry)
    partner.invited_at = timezone.now() - timedelta(days=8)
    partner.save()
    return partner
