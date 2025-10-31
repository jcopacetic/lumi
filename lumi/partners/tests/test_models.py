import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone

from lumi.partners.models import Partner
from lumi.users.models import User

pytestmark = pytest.mark.django_db


class TestPartnerModel:
    """Tests for Partner model"""

    def test_partner_creation(self):
        """Test creating a partner"""
        partner = Partner.objects.create(
            email="test@example.com",
            company_name="Test Company",
            partner_type=Partner.REAL_ESTATE,
        )

        assert partner.email == "test@example.com"
        assert partner.company_name == "Test Company"
        assert partner.partner_type == Partner.REAL_ESTATE
        assert partner.is_active is True
        assert partner.user is None
        assert partner.accepted_at is None
        assert isinstance(partner.invite_token, uuid.UUID)

    def test_partner_str_representation(self):
        """Test string representation of partner"""
        partner = Partner.objects.create(
            email="test@example.com",
            company_name="Acme Corp",
            partner_type=Partner.FAMILY_OFFICE,
        )

        assert str(partner) == "Acme Corp (Family Office)"

    def test_partner_type_choices(self):
        """Test all partner type choices"""
        # Test Real Estate
        partner1 = Partner.objects.create(
            email="re@example.com",
            company_name="RE Company",
            partner_type=Partner.REAL_ESTATE,
        )
        assert partner1.get_partner_type_display() == "Real Estate"

        # Test Family Office
        partner2 = Partner.objects.create(
            email="fo@example.com",
            company_name="FO Company",
            partner_type=Partner.FAMILY_OFFICE,
        )
        assert partner2.get_partner_type_display() == "Family Office"

        # Test Mortgage Broker
        partner3 = Partner.objects.create(
            email="mb@example.com",
            company_name="MB Company",
            partner_type=Partner.MORTGAGE_BROKER,
        )
        assert partner3.get_partner_type_display() == "Mortgage Broker"

    def test_partner_ordering(self):
        """Test that partners are ordered by created_at descending"""
        partner1 = Partner.objects.create(
            email="first@example.com",
            company_name="First",
            partner_type=Partner.REAL_ESTATE,
        )
        partner2 = Partner.objects.create(
            email="second@example.com",
            company_name="Second",
            partner_type=Partner.REAL_ESTATE,
        )

        partners = list(Partner.objects.all())
        assert partners[0] == partner2  # Most recent first
        assert partners[1] == partner1

    def test_email_unique_constraint(self):
        """Test that email must be unique"""
        Partner.objects.create(
            email="unique@example.com",
            company_name="Company 1",
            partner_type=Partner.REAL_ESTATE,
        )

        with pytest.raises(Exception):  # noqa: PT011 B017
            Partner.objects.create(
                email="unique@example.com",
                company_name="Company 2",
                partner_type=Partner.REAL_ESTATE,
            )

    def test_invite_token_unique(self):
        """Test that invite_token is automatically generated and unique"""
        partner1 = Partner.objects.create(
            email="partner1@example.com",
            company_name="Company 1",
            partner_type=Partner.REAL_ESTATE,
        )
        partner2 = Partner.objects.create(
            email="partner2@example.com",
            company_name="Company 2",
            partner_type=Partner.REAL_ESTATE,
        )

        assert partner1.invite_token != partner2.invite_token
        assert isinstance(partner1.invite_token, uuid.UUID)
        assert isinstance(partner2.invite_token, uuid.UUID)


class TestPartnerInviteMethods:
    """Tests for Partner invitation-related methods"""

    def test_send_invite_success(self, partner):
        """Test sending invite email successfully"""
        partner.send_invite()

        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "You're invited to join the Loan Portal"
        assert partner.email in mail.outbox[0].to
        assert mail.outbox[0].from_email == settings.DEFAULT_FROM_EMAIL
        assert str(partner.invite_token) in mail.outbox[0].body

    def test_send_invite_contains_signup_url(self, partner):
        """Test that invite email contains the correct signup URL"""
        partner.send_invite()

        email_body = mail.outbox[0].body
        expected_url = partner.get_invite_url()
        assert expected_url in email_body

    def test_send_invite_failure(self, partner):
        """Test that send_invite raises exception on failure"""
        with patch("lumi.partners.models.send_mail") as mock_send_mail:
            mock_send_mail.side_effect = Exception("SMTP Error")

            with pytest.raises(Exception) as exc_info:  # noqa: PT011
                partner.send_invite()

            assert "SMTP Error" in str(exc_info.value)

    def test_get_invite_url(self, partner):
        """Test generating the full invite URL"""
        url = partner.get_invite_url()

        assert url.startswith(settings.SITE_URL)
        assert str(partner.invite_token) in url
        assert "/partners/signup/" in url

    def test_regenerate_invite_token(self, partner):
        """Test regenerating invite token"""
        old_token = partner.invite_token
        old_invited_at = partner.invited_at

        partner.regenerate_invite_token(save=True)

        assert partner.invite_token != old_token
        assert partner.invited_at > old_invited_at
        assert isinstance(partner.invite_token, uuid.UUID)

    def test_regenerate_invite_token_without_save(self, partner):
        """Test regenerating token without saving to database"""
        old_token = partner.invite_token

        partner.regenerate_invite_token(save=False)
        partner_from_db = Partner.objects.get(pk=partner.pk)

        # Token changed in memory but not in database
        assert partner.invite_token != old_token
        assert partner_from_db.invite_token == old_token

    def test_is_invite_expired_not_expired(self, partner):
        """Test that recent invite is not expired"""
        assert partner.is_invite_expired() is False

    def test_is_invite_expired_expired(self, partner):
        """Test that old invite is expired"""
        partner.invited_at = timezone.now() - timedelta(days=8)
        partner.save()

        assert partner.is_invite_expired() is True

    def test_is_invite_expired_custom_expiry(self, partner):
        """Test custom expiry days parameter"""
        partner.invited_at = timezone.now() - timedelta(days=4)
        partner.save()

        # Not expired with 7 day expiry
        assert partner.is_invite_expired(expiry_days=7) is False

        # Expired with 3 day expiry
        assert partner.is_invite_expired(expiry_days=3) is True

    def test_is_invite_expired_no_invited_at(self):
        """Test that partner with very old invited_at is considered expired"""
        from datetime import timedelta

        partner = Partner.objects.create(
            email="test@example.com",
            company_name="Test",
            partner_type=Partner.REAL_ESTATE,
        )
        # Set invited_at to very long ago instead of None (since it's auto_now_add)
        partner.invited_at = timezone.now() - timedelta(days=365)
        partner.save()

        assert partner.is_invite_expired() is True

    def test_mark_as_accepted(self, partner, user):
        """Test marking invite as accepted"""
        assert partner.accepted_at is None
        assert partner.user is None

        partner.mark_as_accepted(user)

        assert partner.user == user
        assert partner.accepted_at is not None
        assert isinstance(partner.accepted_at, type(timezone.now()))

    def test_mark_as_accepted_updates_database(self, partner, user):
        """Test that mark_as_accepted persists to database"""
        partner.mark_as_accepted(user)

        partner_from_db = Partner.objects.get(pk=partner.pk)
        assert partner_from_db.user == user
        assert partner_from_db.accepted_at is not None


class TestPartnerProperties:
    """Tests for Partner model properties"""

    def test_has_accepted_true(self, partner, user):
        """Test has_accepted returns True when accepted"""
        partner.mark_as_accepted(user)

        assert partner.has_accepted is True

    def test_has_accepted_false_no_user(self, partner):
        """Test has_accepted returns False when no user"""
        assert partner.has_accepted is False

    def test_has_accepted_false_no_accepted_at(self, partner, user):
        """Test has_accepted returns False when user but no accepted_at"""
        partner.user = user
        partner.save()

        assert partner.has_accepted is False

    def test_has_accepted_false_no_user_with_accepted_at(self, partner):
        """Test has_accepted returns False when accepted_at but no user"""
        partner.accepted_at = timezone.now()
        partner.save()

        assert partner.has_accepted is False

    def test_invite_status_accepted(self, partner, user):
        """Test invite_status returns 'Accepted' when accepted"""
        partner.mark_as_accepted(user)

        assert partner.invite_status == "Accepted"

    def test_invite_status_expired(self, partner):
        """Test invite_status returns 'Expired' when expired"""
        partner.invited_at = timezone.now() - timedelta(days=8)
        partner.save()

        assert partner.invite_status == "Expired"

    def test_invite_status_pending(self, partner):
        """Test invite_status returns 'Pending' for valid pending invite"""
        assert partner.invite_status == "Pending"

    def test_invite_status_priority_accepted_over_expired(self, partner, user):
        """Test that accepted status takes priority over expired"""
        # Make it expired
        partner.invited_at = timezone.now() - timedelta(days=8)
        partner.save()

        # Then accept it
        partner.mark_as_accepted(user)

        # Should show as Accepted, not Expired
        assert partner.invite_status == "Accepted"


class TestPartnerUserRelationship:
    """Tests for Partner-User relationship"""

    def test_one_to_one_relationship(self, user):
        """Test that a user can only be linked to one partner"""
        partner = Partner.objects.create(
            email=user.email,
            company_name="Company",
            partner_type=Partner.REAL_ESTATE,
            user=user,
        )

        # Access partner through user
        assert user.partner_profile == partner

        # Trying to create another partner with same user should fail
        with pytest.raises(Exception):  # noqa: PT011 B017
            Partner.objects.create(
                email="different@example.com",
                company_name="Another Company",
                partner_type=Partner.REAL_ESTATE,
                user=user,
            )

    def test_partner_can_exist_without_user(self):
        """Test that partner can exist without a linked user"""
        partner = Partner.objects.create(
            email="test@example.com",
            company_name="Company",
            partner_type=Partner.REAL_ESTATE,
        )

        assert partner.user is None
        assert partner.pk is not None

    def test_cascade_delete(self, user):
        """Test that deleting user cascades to partner"""
        partner = Partner.objects.create(
            email=user.email,
            company_name="Company",
            partner_type=Partner.REAL_ESTATE,
            user=user,
        )

        partner_id = partner.id
        user.delete()

        # Partner should be deleted
        assert not Partner.objects.filter(id=partner_id).exists()


class TestPartnerTimestamps:
    """Tests for Partner timestamp fields"""

    def test_invited_at_auto_set(self):
        """Test that invited_at is automatically set on creation"""
        partner = Partner.objects.create(
            email="test@example.com",
            company_name="Company",
            partner_type=Partner.REAL_ESTATE,
        )

        assert partner.invited_at is not None
        assert isinstance(partner.invited_at, type(timezone.now()))

    def test_created_at_auto_set(self):
        """Test that created_at is automatically set on creation"""
        partner = Partner.objects.create(
            email="test@example.com",
            company_name="Company",
            partner_type=Partner.REAL_ESTATE,
        )

        assert partner.created_at is not None
        assert isinstance(partner.created_at, type(timezone.now()))

    def test_updated_at_auto_updates(self):
        """Test that updated_at is automatically updated on save"""
        partner = Partner.objects.create(
            email="test@example.com",
            company_name="Company",
            partner_type=Partner.REAL_ESTATE,
        )

        original_updated_at = partner.updated_at

        # Wait a tiny bit and update
        partner.company_name = "Updated Company"
        partner.save()

        assert partner.updated_at > original_updated_at


# Fixtures
@pytest.fixture
def partner(db):
    """Create a partner without a user"""
    return Partner.objects.create(
        email="partner@example.com",
        company_name="Test Company",
        partner_type=Partner.REAL_ESTATE,
        is_active=True,
    )


@pytest.fixture
def user(db):
    """Create a regular user"""
    return User.objects.create_user(
        email="testuser@example.com",
        password="testpass123",  # noqa: S106
    )
