from allauth.account.views import SignupView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.views.generic import TemplateView

from lumi.partners.forms import PartnerSignupForm
from lumi.partners.models import Partner


class PartnerSignupView(SignupView):
    """
    Custom signup view that validates partner invite token
    and links the new user to the partner profile
    """

    template_name = "partners/partner_signup.html"
    form_class = PartnerSignupForm

    def dispatch(self, request, *args, **kwargs):
        """Validate token before allowing signup"""
        token = kwargs.get("token")

        if not token:
            messages.error(request, "Invalid or missing invitation token.")
            return redirect("account_login")

        try:
            self.partner = Partner.objects.get(invite_token=token)
        except Partner.DoesNotExist:
            messages.error(request, "Invalid invitation token.")
            return redirect("account_login")

        # Check if already accepted
        if self.partner.has_accepted:
            messages.info(request, "This invitation has already been used.")
            return redirect("account_login")

        # Check if expired
        if self.partner.is_invite_expired():
            messages.error(
                request,
                "This invitation has expired. Please contact support \
                    for a new invitation.",
            )
            return redirect("account_login")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pre-fill email field with partner's email"""
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = kwargs.get("initial", {})
        kwargs["initial"]["email"] = self.partner.email
        return kwargs

    def form_valid(self, form):
        """Link the new user to the partner profile"""
        response = super().form_valid(form)

        # Link the newly created user to the partner
        user = self.user  # Set by parent SignupView
        self.partner.mark_as_accepted(user)

        messages.success(
            self.request,
            f"Welcome to the Loan Portal, {self.partner.company_name}!",
        )

        return response

    def get_context_data(self, **kwargs):
        """Add partner info to template context"""
        context = super().get_context_data(**kwargs)
        context["partner"] = self.partner
        return context


class PartnerDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for logged-in partners"""

    template_name = "partners/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        """Ensure user has a partner profile"""
        try:
            self.partner = request.user.partner_profile
        except Partner.DoesNotExist:
            messages.error(
                request,
                "You don't have access to the partner \
                           portal.",
            )
            return redirect("account_login")

        if not self.partner.is_active:
            return HttpResponseForbidden(
                "Your partner account has been \
                                         deactivated.",
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["partner"] = self.partner
        return context


def validate_partner_token(request):
    """
    Alternative approach: Validate token and redirect to allauth signup
    with token in session. Use this if you want to keep using standard
    allauth signup URL instead of custom partner signup URL.

    URL pattern: ?token=<uuid>
    """
    token = request.GET.get("token")

    if not token:
        messages.error(request, "Missing invitation token.")
        return redirect("account_login")

    try:
        partner = Partner.objects.get(invite_token=token)
    except Partner.DoesNotExist:
        messages.error(request, "Invalid invitation token.")
        return redirect("account_login")

    if partner.has_accepted:
        messages.info(request, "This invitation has already been used.")
        return redirect("account_login")

    if partner.is_invite_expired():
        messages.error(request, "This invitation has expired.")
        return redirect("account_login")

    # Store partner ID in session for use during signup
    request.session["partner_signup_id"] = partner.id
    request.session["partner_email"] = partner.email

    return redirect("account_signup")


def resend_partner_invite(request, pk):
    """
    Admin/staff view to resend invitation to a partner
    Optional feature - remove if not needed
    """
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access required")

    partner = get_object_or_404(Partner, pk=pk)

    if partner.has_accepted:
        messages.warning(
            request,
            f"{partner.company_name} has already accepted their invite.",
        )
    else:
        try:
            partner.regenerate_invite_token(save=True)
            partner.send_invite()
            messages.success(request, f"Invitation resent to {partner.email}")
        except Exception as e:  # noqa: BLE001
            messages.error(request, f"Failed to resend invite: {e!s}")

    return redirect("admin:partners_partner_change", partner.pk)
