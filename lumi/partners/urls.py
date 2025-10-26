from django.urls import path

from . import views

app_name = "partners"

urlpatterns = [
    # Partner signup with token validation
    path(
        "signup/<uuid:token>/",
        views.PartnerSignupView.as_view(),
        name="partner_signup",
    ),
    # Alternative: Token validation redirect (if using standard allauth signup)
    path(
        "validate-invite/",
        views.validate_partner_token,
        name="validate_invite",
    ),
    # Partner dashboard (after login)
    path(
        "dashboard/",
        views.PartnerDashboardView.as_view(),
        name="dashboard",
    ),
    # Admin actions (optional - for partner self-service)
    path(
        "resend-invite/<int:pk>/",
        views.resend_partner_invite,
        name="resend_invite",
    ),
]
