from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from rolepermissions.mixins import HasRoleMixin

from lumi.loans.models import DepositLoanApplication
from lumi.loans.models import MarketingLoanApplication
from lumi.loans.models import RenovationLoanApplication
from lumi.partners.models import Partner


class AdminRequiredMixin(HasRoleMixin, LoginRequiredMixin):
    """Mixin to require Admin role"""

    allowed_roles = ["admin"]

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect("loans:all_loan_applications")


class PartnerListView(AdminRequiredMixin, ListView):
    """List all partners with stats and filters"""

    model = Partner
    template_name = "manager/partner_list.html"
    context_object_name = "partners"
    paginate_by = 20

    def get_queryset(self):
        queryset = Partner.objects.select_related("user").order_by("-created_at")

        # Filter by partner type
        partner_type = self.request.GET.get("partner_type")
        if partner_type:
            queryset = queryset.filter(partner_type=partner_type)

        # Filter by status
        status = self.request.GET.get("status")
        if status == "accepted":
            queryset = queryset.filter(accepted_at__isnull=False)
        elif status == "pending":
            queryset = queryset.filter(accepted_at__isnull=True)
        elif status == "expired":
            # Partners with pending invites older than 7 days
            queryset = queryset.filter(
                accepted_at__isnull=True,
                invited_at__lt=timezone.now() - timezone.timedelta(days=7),
            )

        # Filter by active status
        is_active = self.request.GET.get("is_active")
        if is_active == "true":
            queryset = queryset.filter(is_active=True)
        elif is_active == "false":
            queryset = queryset.filter(is_active=False)

        # Search by company name or email
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) | Q(email__icontains=search),
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter values for template
        context["partner_type_filter"] = self.request.GET.get("partner_type", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["is_active_filter"] = self.request.GET.get("is_active", "")
        context["search_query"] = self.request.GET.get("search", "")

        # Partner type choices for filter dropdown
        context["partner_type_choices"] = Partner.PARTNER_TYPE_CHOICES

        # Summary statistics
        all_partners = Partner.objects.all()
        context["total_partners"] = all_partners.count()
        context["active_partners"] = all_partners.filter(is_active=True).count()
        context["pending_invites"] = all_partners.filter(
            accepted_at__isnull=True,
        ).count()
        context["accepted_partners"] = all_partners.filter(
            accepted_at__isnull=False,
        ).count()

        # Partner type breakdown
        context["partner_type_stats"] = {
            "real_estate": all_partners.filter(partner_type="real_estate").count(),
            "family_office": all_partners.filter(partner_type="family_office").count(),
            "mortgage_broker": all_partners.filter(
                partner_type="mortgage_broker",
            ).count(),
        }

        return context


class PartnerDetailView(AdminRequiredMixin, DetailView):
    """Detailed view of a single partner with all their applications"""

    model = Partner
    template_name = "manager/partner_detail.html"
    context_object_name = "partner"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        partner = self.object

        # Get all applications by this partner
        marketing_apps = MarketingLoanApplication.objects.filter(partner=partner)
        renovation_apps = RenovationLoanApplication.objects.filter(partner=partner)
        deposit_apps = DepositLoanApplication.objects.filter(partner=partner)

        # Application counts by status
        context["total_applications"] = (
            marketing_apps.count() + renovation_apps.count() + deposit_apps.count()
        )

        # Status breakdown across all loan types
        all_statuses = []
        for app_set in [marketing_apps, renovation_apps, deposit_apps]:
            all_statuses.extend(app_set.values_list("status", flat=True))

        from collections import Counter

        status_counts = Counter(all_statuses)

        context["status_breakdown"] = {
            "draft": status_counts.get("draft", 0),
            "submitted": status_counts.get("submitted", 0),
            "under_review": status_counts.get("under_review", 0),
            "approved": status_counts.get("approved", 0),
            "rejected": status_counts.get("rejected", 0),
            "withdrawn": status_counts.get("withdrawn", 0),
        }

        # Applications by type
        context["marketing_applications"] = marketing_apps.order_by("-created_at")[:10]
        context["renovation_applications"] = renovation_apps.order_by("-created_at")[
            :10
        ]
        context["deposit_applications"] = deposit_apps.order_by("-created_at")[:10]

        context["marketing_count"] = marketing_apps.count()
        context["renovation_count"] = renovation_apps.count()
        context["deposit_count"] = deposit_apps.count()

        # Financial metrics (total loan amounts by status)
        context["total_loan_amount_submitted"] = sum(
            [
                marketing_apps.filter(
                    status__in=["submitted", "under_review"],
                ).aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
                renovation_apps.filter(
                    status__in=["submitted", "under_review"],
                ).aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
                deposit_apps.filter(status__in=["submitted", "under_review"]).aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
            ],
        )

        context["total_loan_amount_approved"] = sum(
            [
                marketing_apps.filter(status="approved").aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
                renovation_apps.filter(status="approved").aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
                deposit_apps.filter(status="approved").aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
            ],
        )

        # Recent activity (last 10 applications across all types)
        recent_marketing = list(marketing_apps.order_by("-updated_at")[:10])
        recent_renovation = list(renovation_apps.order_by("-updated_at")[:10])
        recent_deposit = list(deposit_apps.order_by("-updated_at")[:10])

        # Add loan_type attribute for template access
        for app in recent_marketing:
            app.loan_type = "marketing"
        for app in recent_renovation:
            app.loan_type = "renovation"
        for app in recent_deposit:
            app.loan_type = "deposit"

        # Combine and sort by updated_at
        recent_activity = sorted(
            recent_marketing + recent_renovation + recent_deposit,
            key=lambda x: x.updated_at,
            reverse=True,
        )[:10]

        context["recent_activity"] = recent_activity

        return context


class PartnerCreateView(AdminRequiredMixin, CreateView):
    """Create a new partner and send invitation"""

    model = Partner
    template_name = "manager/partner_form.html"
    fields = ["email", "company_name", "partner_type", "is_active"]
    success_url = reverse_lazy("manager:partner_list")

    def form_valid(self, form):
        response = super().form_valid(form)

        # Send invitation email
        try:
            self.object.send_invite()
            messages.success(
                self.request,
                f"Partner '{self.object.company_name}' created and invitation \
                    sent to {self.object.email}",
            )
        except Exception as e:  # noqa: BLE001
            messages.warning(
                self.request,
                f"Partner created but failed to send invitation: {e!s}",
            )

        return response


class PartnerUpdateView(AdminRequiredMixin, UpdateView):
    """Update partner details"""

    model = Partner
    template_name = "manager/partner_form.html"
    fields = ["email", "company_name", "partner_type", "is_active"]

    def get_success_url(self):
        return reverse("manager:partner_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Partner '{self.object.company_name}' updated successfully",
        )
        return response


def partner_resend_invite(request, pk):
    """Resend invitation to a partner"""
    if not request.user.has_role("admin"):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect("loans:all_loan_applications")

    partner = get_object_or_404(Partner, pk=pk)

    if partner.has_accepted:
        messages.warning(
            request,
            f"{partner.company_name} has already accepted their invitation.",
        )
    else:
        try:
            partner.regenerate_invite_token(save=True)
            partner.send_invite()
            messages.success(request, f"Invitation resent to {partner.email}")
        except Exception as e:  # noqa: BLE001
            messages.error(request, f"Failed to resend invitation: {e!s}")

    return redirect("manager:partner_detail", pk=partner.pk)


def partner_toggle_active(request, pk):
    """Toggle partner active status"""
    if not request.user.has_role("admin"):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect("loans:all_loan_applications")

    partner = get_object_or_404(Partner, pk=pk)
    partner.is_active = not partner.is_active
    partner.save()

    status = "activated" if partner.is_active else "deactivated"
    messages.success(request, f"Partner '{partner.company_name}' has been {status}")

    return redirect("manager:partner_detail", pk=partner.pk)


class ManagerDashboardView(AdminRequiredMixin, ListView):
    """Main dashboard for Luminate admins"""

    model = Partner
    template_name = "manager/dashboard.html"
    context_object_name = "recent_partners"

    def get_queryset(self):
        return Partner.objects.order_by("-created_at")[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Partner statistics
        context["total_partners"] = Partner.objects.count()
        context["active_partners"] = Partner.objects.filter(is_active=True).count()
        context["pending_invites"] = Partner.objects.filter(
            accepted_at__isnull=True,
        ).count()

        # Application statistics (across all types)
        marketing_apps = MarketingLoanApplication.objects.all()
        renovation_apps = RenovationLoanApplication.objects.all()
        deposit_apps = DepositLoanApplication.objects.all()

        context["total_applications"] = (
            marketing_apps.count() + renovation_apps.count() + deposit_apps.count()
        )

        context["submitted_applications"] = (
            marketing_apps.filter(status="submitted").count()
            + renovation_apps.filter(status="submitted").count()
            + deposit_apps.filter(status="submitted").count()
        )

        context["under_review_applications"] = (
            marketing_apps.filter(status="under_review").count()
            + renovation_apps.filter(status="under_review").count()
            + deposit_apps.filter(status="under_review").count()
        )

        context["approved_applications"] = (
            marketing_apps.filter(status="approved").count()
            + renovation_apps.filter(status="approved").count()
            + deposit_apps.filter(status="approved").count()
        )

        # Loan type breakdown
        context["marketing_count"] = marketing_apps.count()
        context["renovation_count"] = renovation_apps.count()
        context["deposit_count"] = deposit_apps.count()

        # Recent applications across all types
        recent_marketing = list(
            marketing_apps.select_related("partner").order_by("-created_at")[:5],
        )
        recent_renovation = list(
            renovation_apps.select_related("partner").order_by("-created_at")[:5],
        )
        recent_deposit = list(
            deposit_apps.select_related("partner").order_by("-created_at")[:5],
        )

        # Add loan_type attribute for template access
        for app in recent_marketing:
            app.loan_type = "marketing"
        for app in recent_renovation:
            app.loan_type = "renovation"
        for app in recent_deposit:
            app.loan_type = "deposit"

        recent_activity = sorted(
            recent_marketing + recent_renovation + recent_deposit,
            key=lambda x: x.created_at,
            reverse=True,
        )[:10]

        context["recent_applications"] = recent_activity

        # Financial metrics
        context["total_loan_value_pending"] = sum(
            [
                marketing_apps.filter(
                    status__in=["submitted", "under_review"],
                ).aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
                renovation_apps.filter(
                    status__in=["submitted", "under_review"],
                ).aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
                deposit_apps.filter(status__in=["submitted", "under_review"]).aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
            ],
        )

        context["total_loan_value_approved"] = sum(
            [
                marketing_apps.filter(status="approved").aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
                renovation_apps.filter(status="approved").aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
                deposit_apps.filter(status="approved").aggregate(
                    total=Sum("loan_amount"),
                )["total"]
                or 0,
            ],
        )

        return context
