from django.urls import path

from . import views

app_name = "manager"

urlpatterns = [
    # Dashboard
    path(
        "",
        views.ManagerDashboardView.as_view(),
        name="dashboard",
    ),
    # Partner manager
    path(
        "partners/",
        views.PartnerListView.as_view(),
        name="partner_list",
    ),
    path(
        "partners/new/",
        views.PartnerCreateView.as_view(),
        name="partner_create",
    ),
    path(
        "partners/<int:pk>/",
        views.PartnerDetailView.as_view(),
        name="partner_detail",
    ),
    path(
        "partners/<int:pk>/edit/",
        views.PartnerUpdateView.as_view(),
        name="partner_edit",
    ),
    path(
        "partners/<int:pk>/resend-invite/",
        views.partner_resend_invite,
        name="partner_resend_invite",
    ),
    path(
        "partners/<int:pk>/toggle-active/",
        views.partner_toggle_active,
        name="partner_toggle_active",
    ),
]
