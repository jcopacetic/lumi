import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from model_utils.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    Notification model for real-time user notifications.
    Supports HTMX + Channels WebSocket delivery.
    """

    class NotificationType(models.TextChoices):
        ACCOUNT = "account", "Account"
        MARKETING = "marketing", "Marketing"
        FEATURE = "feature", "Feature/Function"
        SYSTEM = "system", "System"
        APPLICATION = "application", "Application"
        SECURITY = "security", "Security"

    class NotificationStatus(models.TextChoices):
        UNSEEN = "unseen", "Unseen"
        SEEN = "seen", "Seen"
        ARCHIVED = "archived", "Archived"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    # Primary identifier
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    slug = models.SlugField(
        max_length=36,
        unique=True,
        editable=False,
        help_text="Auto-generated from UUID",
    )

    # User relationship
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )

    # Content fields
    title = models.CharField(
        max_length=200,
        help_text="Notification headline",
    )
    html = models.TextField(
        help_text="HTML content (sanitized: p, a, strong, em, br only)",
    )

    # Classification
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    status = models.CharField(
        max_length=10,
        choices=NotificationStatus.choices,
        default=NotificationStatus.UNSEEN,
        db_index=True,
    )

    # Optional action link
    action_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional URL for notification action",
    )
    action_text = models.CharField(
        max_length=50,
        blank=True,
        default="View",
        help_text="Text for action button",
    )

    # Tracking
    seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When notification was first seen",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date",
    )

    # Metadata for tracking source
    source = models.CharField(
        max_length=100,
        blank=True,
        help_text="System source (e.g., 'loan_application', 'user_registration')",
    )
    source_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Related object ID if applicable",
    )

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["user", "status", "-created"]),
            models.Index(fields=["user", "notification_type"]),
            models.Index(fields=["-created"]),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"Notification: {self.title} ({self.status})"

    def save(self, *args, **kwargs):
        """Auto-generate slug from UUID on creation"""
        if not self.slug:
            self.slug = str(self.uuid)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return URL to view this notification"""
        return reverse("notifications:detail", kwargs={"slug": self.slug})

    # === Core Methods ===

    def mark_as_seen(self):
        """Mark notification as seen"""
        if self.status == self.NotificationStatus.UNSEEN:
            self.status = self.NotificationStatus.SEEN
            self.seen_at = timezone.now()
            self.save(update_fields=["status", "seen_at", "modified"])
            return True
        return False

    def mark_as_unseen(self):
        """Mark notification as unseen (for testing/admin)"""
        self.status = self.NotificationStatus.UNSEEN
        self.seen_at = None
        self.save(update_fields=["status", "seen_at", "modified"])

    def archive(self):
        """Archive this notification"""
        self.status = self.NotificationStatus.ARCHIVED
        self.save(update_fields=["status", "modified"])

    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def soft_delete(self):
        """
        Soft delete by archiving instead of actual deletion.
        Maintains audit trail for NZ compliance.
        """
        self.archive()

    # === Properties ===

    @property
    def is_seen(self):
        """Check if notification has been seen"""
        return self.status != self.NotificationStatus.UNSEEN

    @property
    def is_high_priority(self):
        """Check if notification is high priority"""
        return self.priority in [self.Priority.HIGH, self.Priority.URGENT]

    @property
    def css_class(self):
        """Return Bootstrap CSS class based on notification type"""
        return {
            self.NotificationType.ACCOUNT: "primary",
            self.NotificationType.MARKETING: "info",
            self.NotificationType.FEATURE: "success",
            self.NotificationType.SYSTEM: "secondary",
            self.NotificationType.APPLICATION: "warning",
            self.NotificationType.SECURITY: "danger",
        }.get(self.notification_type, "secondary")

    @property
    def icon(self):
        """Return Bootstrap icon class based on notification type"""
        return {
            self.NotificationType.ACCOUNT: "bi-person-circle",
            self.NotificationType.MARKETING: "bi-megaphone",
            self.NotificationType.FEATURE: "bi-star",
            self.NotificationType.SYSTEM: "bi-gear",
            self.NotificationType.APPLICATION: "bi-file-earmark-text",
            self.NotificationType.SECURITY: "bi-shield-exclamation",
        }.get(self.notification_type, "bi-bell")

    # === Class Methods ===

    @classmethod
    def create_notification(cls, user, **kwargs):
        """
        Factory method to create and optionally send notification.

        Usage:
            Notification.create_notification(
                user=user,
                title="New Loan Application",
                html="<p>Application #12345 requires review.</p>",
                notification_type="application",
                priority="high",
                action_url="/applications/12345/",
                source="loan_application",
                source_id="12345",
            )
        """
        defaults = {
            "title": "",
            "html": "",
            "notification_type": cls.NotificationType.SYSTEM,
            "priority": cls.Priority.NORMAL,
            "action_url": "",
            "action_text": "View",
            "source": "",
            "source_id": "",
            "expires_at": None,
        }

        defaults.update(kwargs)
        return cls.objects.create(user=user, **defaults)

    @classmethod
    def get_user_notifications(
        cls,
        user,
        status=None,
        notification_type=None,
        limit=50,
    ):
        """
        Get notifications for a user with optional filters.
        Excludes expired notifications.
        """
        qs = cls.objects.filter(user=user)

        if status:
            qs = qs.filter(status=status)

        if notification_type:
            qs = qs.filter(notification_type=notification_type)

        # Exclude expired
        now = timezone.now()
        return qs.filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now),
        )[:limit]

    @classmethod
    def get_unseen_count(cls, user):
        """Get count of unseen notifications for user"""
        now = timezone.now()
        return (
            cls.objects.filter(
                user=user,
                status=cls.NotificationStatus.UNSEEN,
            )
            .filter(
                models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now),
            )
            .count()
        )

    @classmethod
    def mark_all_as_seen(cls, user):
        """Mark all unseen notifications as seen for user"""
        now = timezone.now()
        return cls.objects.filter(
            user=user,
            status=cls.NotificationStatus.UNSEEN,
        ).update(
            status=cls.NotificationStatus.SEEN,
            seen_at=now,
        )

    @classmethod
    def cleanup_old_notifications(cls, days=90):
        """
        Archive old seen notifications for compliance.
        Call this via Celery periodic task.
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return cls.objects.filter(
            status=cls.NotificationStatus.SEEN,
            modified__lt=cutoff,
        ).update(status=cls.NotificationStatus.ARCHIVED)
