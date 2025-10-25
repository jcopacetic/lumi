from django.urls import path

from lumi.loans.views import all_loan_applications
from lumi.loans.views import application_detail
from lumi.loans.views import deposit_loan_application
from lumi.loans.views import deposit_loan_application_continue
from lumi.loans.views import deposit_loan_application_start
from lumi.loans.views import deposit_loan_application_step
from lumi.loans.views import deposit_loan_application_submit
from lumi.loans.views import marketing_loan_application
from lumi.loans.views import marketing_loan_application_continue
from lumi.loans.views import marketing_loan_application_start
from lumi.loans.views import marketing_loan_application_step
from lumi.loans.views import marketing_loan_application_submit
from lumi.loans.views import partner_applications_list
from lumi.loans.views import renovation_loan_application
from lumi.loans.views import renovation_loan_application_continue
from lumi.loans.views import renovation_loan_application_start
from lumi.loans.views import renovation_loan_application_step
from lumi.loans.views import renovation_loan_application_submit

app_name = "loans"

urlpatterns = [
    # Dashboard
    path("", all_loan_applications, name="all_loan_applications"),
    # Application lists and details
    path("applications/", partner_applications_list, name="all_applications_list"),
    path(
        "applications/<str:loan_type>/",
        partner_applications_list,
        name="applications_by_type",
    ),
    path(
        "applications/<str:loan_type>/<uuid:pk>/",
        application_detail,
        name="application_detail",
    ),
    # Marketing Loan URLs
    path("marketing/", marketing_loan_application, name="marketing_loan_application"),
    path(
        "marketing/start/",
        marketing_loan_application_start,
        name="marketing_loan_application_start",
    ),
    path(
        "marketing/continue/<uuid:pk>/",
        marketing_loan_application_continue,
        name="marketing_loan_application_continue",
    ),
    path(
        "marketing/step/<int:step>/",
        marketing_loan_application_step,
        name="marketing_loan_application_step",
    ),
    path(
        "marketing/submit/",
        marketing_loan_application_submit,
        name="marketing_loan_application_submit",
    ),
    # Renovation Loan URLs
    path(
        "renovation/",
        renovation_loan_application,
        name="renovation_loan_application",
    ),
    path(
        "renovation/start/",
        renovation_loan_application_start,
        name="renovation_loan_application_start",
    ),
    path(
        "renovation/continue/<uuid:pk>/",
        renovation_loan_application_continue,
        name="renovation_loan_application_continue",
    ),
    path(
        "renovation/step/<int:step>/",
        renovation_loan_application_step,
        name="renovation_loan_application_step",
    ),
    path(
        "renovation/submit/",
        renovation_loan_application_submit,
        name="renovation_loan_application_submit",
    ),
    # Deposit Loan URLs
    path("deposit/", deposit_loan_application, name="deposit_loan_application"),
    path(
        "deposit/start/",
        deposit_loan_application_start,
        name="deposit_loan_application_start",
    ),
    path(
        "deposit/continue/<uuid:pk>/",
        deposit_loan_application_continue,
        name="deposit_loan_application_continue",
    ),
    path(
        "deposit/step/<int:step>/",
        deposit_loan_application_step,
        name="deposit_loan_application_step",
    ),
    path(
        "deposit/submit/",
        deposit_loan_application_submit,
        name="deposit_loan_application_submit",
    ),
]
