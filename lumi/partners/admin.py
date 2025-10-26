from django.contrib import admin
from django.utils.html import format_html

from .models import Partner


@admin.action(description="Send invite email to selected partners")
def send_invite_action(modeladmin, request, queryset):
    """Admin action to send invites to multiple partners"""
    sent_count = 0
    failed_count = 0

    for partner in queryset:
        try:
            partner.send_invite()
            sent_count += 1
        except Exception as e:  # noqa: BLE001
            failed_count += 1
            modeladmin.message_user(
                request,
                f"Failed to send invite to {partner.email}: {e!s}",
                level="ERROR",
            )

    if sent_count > 0:
        modeladmin.message_user(
            request,
            f"Successfully sent {sent_count} invitation(s).",
            level="SUCCESS",
        )


@admin.action(description="Regenerate invite tokens for selected partners")
def regenerate_tokens_action(modeladmin, request, queryset):
    """Admin action to regenerate tokens and optionally resend invites"""
    count = 0
    for partner in queryset:
        if not partner.has_accepted:
            partner.regenerate_invite_token(save=True)
            count += 1

    modeladmin.message_user(
        request,
        f"Regenerated {count} invite token(s).",
        level="SUCCESS",
    )


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = [
        "company_name",
        "email",
        "partner_type",
        "invite_status_badge",
        "invited_at",
        "accepted_at",
        "is_active",
    ]
    list_filter = [
        "partner_type",
        "is_active",
        "invited_at",
        "accepted_at",
    ]
    search_fields = [
        "company_name",
        "email",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    readonly_fields = [
        "invite_token",
        "invited_at",
        "accepted_at",
        "created_at",
        "updated_at",
        "invite_url_display",
        "invite_status",
    ]
    fieldsets = (
        (
            "Partner Information",
            {
                "fields": (
                    "company_name",
                    "email",
                    "partner_type",
                    "is_active",
                ),
            },
        ),
        (
            "User Account",
            {
                "fields": ("user",),
                "description": "Linked after partner accepts invitation",
            },
        ),
        (
            "Invitation Details",
            {
                "fields": (
                    "invite_token",
                    "invite_url_display",
                    "invite_status",
                    "invited_at",
                    "accepted_at",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    actions = [send_invite_action, regenerate_tokens_action]

    @admin.display(
        description="Status",
    )
    def invite_status_badge(self, obj):
        """Display colored badge for invite status"""
        status = obj.invite_status
        colors = {
            "Accepted": "green",
            "Pending": "orange",
            "Expired": "red",
        }
        color = colors.get(status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            status,
        )

    @admin.display(
        description="Invite URL",
    )
    def invite_url_display(self, obj):
        """Display clickable invite URL in admin"""
        if obj.invite_token:
            url = obj.get_invite_url()
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return "-"

    def save_model(self, request, obj, form, change):
        """Send invite email when creating new partner"""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new and not obj.has_accepted:
            try:
                obj.send_invite()
                self.message_user(
                    request,
                    f"Partner created and invite sent to {obj.email}",
                    level="SUCCESS",
                )
            except Exception as e:  # noqa: BLE001
                self.message_user(
                    request,
                    f"Partner created but failed to send invite: {e!s}",
                    level="WARNING",
                )
