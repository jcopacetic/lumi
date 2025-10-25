import logging
from datetime import date
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone

from lumi.loans.forms import ApplicationRetrievalForm
from lumi.loans.forms import BaseApplicationForm
from lumi.loans.forms import DepositApplicationForm
from lumi.loans.forms import MarketingApplicationForm
from lumi.loans.forms import RenovationApplicationForm
from lumi.loans.models import DepositLoanApplication
from lumi.loans.models import MarketingLoanApplication
from lumi.loans.models import RenovationLoanApplication

logger = logging.getLogger(__name__)


# Helper function to get partner from logged-in user
def get_partner(user):
    """Get the partner profile for the logged-in user"""
    try:
        return user.partner_profile
    except AttributeError:
        return None


# Dashboard view showing all loan types available to this partner
@login_required
def all_loan_applications(request):
    """Dashboard showing available loan types and partner's applications"""
    partner = get_partner(request.user)

    if not partner:
        messages.error(request, "Partner profile not found. Please contact support.")
        return redirect("home")

    # Get partner's recent applications across all types
    marketing_apps = MarketingLoanApplication.objects.filter(
        partner=partner,
    ).order_by("-updated_at")[:5]

    renovation_apps = RenovationLoanApplication.objects.filter(
        partner=partner,
    ).order_by("-updated_at")[:5]

    deposit_apps = DepositLoanApplication.objects.filter(
        partner=partner,
    ).order_by("-updated_at")[:5]

    # Get draft applications count for each type
    marketing_drafts = MarketingLoanApplication.objects.filter(
        partner=partner,
        status="draft",
    ).count()

    renovation_drafts = RenovationLoanApplication.objects.filter(
        partner=partner,
        status="draft",
    ).count()

    deposit_drafts = DepositLoanApplication.objects.filter(
        partner=partner,
        status="draft",
    ).count()

    context = {
        "partner": partner,
        "marketing_apps": marketing_apps,
        "renovation_apps": renovation_apps,
        "deposit_apps": deposit_apps,
        "marketing_drafts": marketing_drafts,
        "renovation_drafts": renovation_drafts,
        "deposit_drafts": deposit_drafts,
    }

    return render(request, "loans/all_loan_applications.html", context)


# ==================== MARKETING LOAN VIEWS ====================


@login_required
def marketing_loan_application(request):
    """Landing page for marketing loans with option to start new or continue"""
    partner = get_partner(request.user)

    # Show recent draft applications
    draft_applications = MarketingLoanApplication.objects.filter(
        partner=partner,
        status="draft",
    ).order_by("-updated_at")[:10]

    # Handle retrieval form
    retrieval_form = ApplicationRetrievalForm()

    if request.method == "POST" and "retrieve_application" in request.POST:
        retrieval_form = ApplicationRetrievalForm(request.POST)
        if retrieval_form.is_valid():
            email = retrieval_form.cleaned_data["customer_email"]
            dob = retrieval_form.cleaned_data["customer_date_of_birth"]

            applications = MarketingLoanApplication.find_application(email, dob)
            applications = applications.filter(partner=partner, status="draft")

            if applications.exists():
                app = applications.first()
                return redirect("loans:marketing_loan_application_continue", pk=app.id)
            messages.warning(request, "No draft application found with those details.")

    context = {
        "partner": partner,
        "draft_applications": draft_applications,
        "retrieval_form": retrieval_form,
    }

    return render(request, "loans/marketing_loan_application.html", context)


@login_required
def marketing_loan_application_start(request):
    """Start a new marketing loan application"""
    # Clear any existing session data
    for key in list(request.session.keys()):
        if key.startswith("marketing_"):
            del request.session[key]

    return redirect("loans:marketing_loan_application_step", step=1)


@login_required
def marketing_loan_application_continue(request, pk):
    """Continue an existing draft application"""
    partner = get_partner(request.user)
    application = get_object_or_404(
        MarketingLoanApplication,
        id=pk,
        partner=partner,
        status="draft",
    )

    # Load application data into session
    request.session["marketing_application_id"] = str(application.id)

    # Populate step 1 data - INCLUDING NEW NZ FIELDS
    request.session["marketing_step_1_data"] = {
        "customer_email": application.customer_email,
        "customer_date_of_birth": application.customer_date_of_birth.isoformat(),
        "first_name": application.first_name,
        "last_name": application.last_name,
        "phone_number": application.phone_number,
        "street_address": application.street_address,
        "suburb": application.suburb,
        "city": application.city,
        "postcode": application.postcode,
        "region": application.region,
        "annual_income": str(application.annual_income),
        "employment_status": application.employment_status,
        "employer_name": application.employer_name,
        "ird_number": application.ird_number or "",
        "loan_amount": str(application.loan_amount),
        "loan_purpose": application.loan_purpose,
    }

    # Populate step 2 data if exists - INCLUDING NEW NZ FIELDS
    if application.business_name:
        request.session["marketing_step_2_data"] = {
            "business_name": application.business_name,
            "business_type": application.business_type,
            "years_in_business": application.years_in_business,
            "nzbn": application.nzbn or "",
            "gst_registered": application.gst_registered,
            "marketing_campaign_description": application.marketing_campaign_description,  # noqa: E501
            "expected_roi": application.expected_roi,
            "target_audience": application.target_audience,
            "digital_marketing_budget": str(application.digital_marketing_budget)
            if application.digital_marketing_budget
            else "",
            "traditional_marketing_budget": str(
                application.traditional_marketing_budget,
            )
            if application.traditional_marketing_budget
            else "",
        }

    messages.info(request, f"Continuing application {application.application_id}")
    return redirect("loans:marketing_loan_application_step", step=1)


@login_required
def marketing_loan_application_step(request, step):
    """Handle multi-step marketing loan application"""
    partner = get_partner(request.user)

    forms = [BaseApplicationForm, MarketingApplicationForm]

    if step < 1 or step > len(forms):
        return redirect("loans:marketing_loan_application_start")

    form_class = forms[step - 1]
    session_key = f"marketing_step_{step}_data"

    if request.method == "POST":
        form = form_class(request.POST)

        # Handle save as draft
        if "save_draft" in request.POST:
            if form.is_valid():
                # Serialize for session
                cleaned_data = _serialize_form_data(form.cleaned_data)
                request.session[session_key] = cleaned_data
                _save_marketing_draft(request, partner)
                messages.success(request, "Application saved as draft.")
                return redirect("loans:marketing_loan_application")

        # Handle next step
        elif form.is_valid():
            # Serialize date fields for session storage
            cleaned_data = _serialize_form_data(form.cleaned_data)
            request.session[session_key] = cleaned_data
            logger.info("Partner %s completed step %s", request.user.username, step)

            next_step = step + 1
            if next_step > len(forms):
                return redirect("loans:marketing_loan_application_submit")
            return redirect("loans:marketing_loan_application_step", step=next_step)
        else:
            logger.warning(
                "Invalid submission at step %s by %s",
                step,
                request.user.email,
            )
    else:
        initial_data = request.session.get(session_key, {})
        form = form_class(initial=initial_data)

    context = {
        "form": form,
        "step": step,
        "total_steps": len(forms),
        "title": "Marketing Loan Application",
        "loan_type": "marketing",
    }

    return render(request, "loans/loan_application_step.html", context)


def _serialize_form_data(cleaned_data):
    """Helper to serialize form data for session storage"""
    serialized = cleaned_data.copy()
    for key, value in serialized.items():
        if isinstance(value, date | datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, Decimal):
            # Convert Decimals to string to preserve precision
            serialized[key] = str(value)
        elif value is None:
            serialized[key] = ""
        elif isinstance(value, bool):
            serialized[key] = value  # leave booleans unchanged
    return serialized


def _save_marketing_draft(request, partner):
    """Helper to save marketing application as draft"""
    from datetime import datetime

    step_1 = request.session.get("marketing_step_1_data", {})
    step_2 = request.session.get("marketing_step_2_data", {})

    if not step_1:
        return None

    # Convert date string back to date object
    dob_str = step_1.get("customer_date_of_birth")
    if isinstance(dob_str, str):
        dob = datetime.fromisoformat(dob_str).date()
    else:
        dob = dob_str

    # Check if continuing existing application
    app_id = request.session.get("marketing_application_id")
    if app_id:
        try:
            application = MarketingLoanApplication.objects.get(
                id=app_id,
                partner=partner,
            )
        except MarketingLoanApplication.DoesNotExist:
            application = MarketingLoanApplication(partner=partner)
    else:
        application = MarketingLoanApplication(partner=partner)

    # Update base fields from step 1
    for field, value in step_1.items():
        if field == "customer_date_of_birth":
            setattr(application, field, dob)
        elif value != "" and value is not None:
            setattr(application, field, value)

    # Update marketing-specific fields from step 2
    for field, value in step_2.items():
        if value != "" and value is not None:
            setattr(application, field, value)

    application.save()
    request.session["marketing_application_id"] = str(application.id)

    return application


@login_required
def marketing_loan_application_submit(request):
    """Final submission of marketing loan application"""
    partner = get_partner(request.user)

    # Save the complete application
    application = _save_marketing_draft(request, partner)

    if not application:
        messages.error(request, "No application data found. Please start again.")
        return redirect("loans:marketing_loan_application_start")

    # Update status to submitted
    application.status = "submitted"
    application.submitted_at = timezone.now()
    application.save()

    logger.info(
        "Marketing loan application %s submitted by %s",
        application.application_id,
        request.user.username,
    )

    # Clear session data
    for key in list(request.session.keys()):
        if key.startswith("marketing_"):
            del request.session[key]

    messages.success(
        request,
        "Marketing loan application submitted successfully! Reference: ",
        application.application_id,
    )
    return redirect("loans:marketing_loan_application")


# ==================== RENOVATION LOAN VIEWS ====================


@login_required
def renovation_loan_application(request):
    """Landing page for renovation loans"""
    partner = get_partner(request.user)

    draft_applications = RenovationLoanApplication.objects.filter(
        partner=partner,
        status="draft",
    ).order_by("-updated_at")[:10]

    retrieval_form = ApplicationRetrievalForm()

    if request.method == "POST" and "retrieve_application" in request.POST:
        retrieval_form = ApplicationRetrievalForm(request.POST)
        if retrieval_form.is_valid():
            email = retrieval_form.cleaned_data["customer_email"]
            dob = retrieval_form.cleaned_data["customer_date_of_birth"]

            applications = RenovationLoanApplication.find_application(email, dob)
            applications = applications.filter(partner=partner, status="draft")

            if applications.exists():
                app = applications.first()
                return redirect("loans:renovation_loan_application_continue", pk=app.id)
            messages.warning(request, "No draft application found with those details.")

    context = {
        "partner": partner,
        "draft_applications": draft_applications,
        "retrieval_form": retrieval_form,
    }

    return render(request, "loans/renovation_loan_application.html", context)


@login_required
def renovation_loan_application_start(request):
    """Start a new renovation loan application"""
    for key in list(request.session.keys()):
        if key.startswith("renovation_"):
            del request.session[key]

    return redirect("loans:renovation_loan_application_step", step=1)


@login_required
def renovation_loan_application_continue(request, pk):
    """Continue an existing draft renovation application"""
    partner = get_partner(request.user)
    application = get_object_or_404(
        RenovationLoanApplication,
        id=pk,
        partner=partner,
        status="draft",
    )

    request.session["renovation_application_id"] = str(application.id)

    # Populate step 1 data (base fields) - INCLUDING NEW NZ FIELDS
    request.session["renovation_step_1_data"] = {
        "customer_email": application.customer_email,
        "customer_date_of_birth": application.customer_date_of_birth.isoformat(),
        "first_name": application.first_name,
        "last_name": application.last_name,
        "phone_number": application.phone_number,
        "street_address": application.street_address,
        "suburb": application.suburb,
        "city": application.city,
        "postcode": application.postcode,
        "region": application.region,
        "annual_income": str(application.annual_income),
        "employment_status": application.employment_status,
        "employer_name": application.employer_name,
        "ird_number": application.ird_number or "",
        "loan_amount": str(application.loan_amount),
        "loan_purpose": application.loan_purpose,
    }

    # Populate step 2 data (renovation-specific) - INCLUDING NEW NZ FIELDS
    if application.property_address:
        request.session["renovation_step_2_data"] = {
            "property_address": application.property_address,
            "property_suburb": application.property_suburb,
            "property_city": application.property_city,
            "property_postcode": application.property_postcode,
            "property_region": application.property_region,
            "property_type": application.property_type,
            "property_ownership": application.property_ownership,
            "renovation_description": application.renovation_description,
            "renovation_type": application.renovation_type,
            "estimated_property_value_before": str(
                application.estimated_property_value_before,
            ),
            "estimated_property_value_after": str(
                application.estimated_property_value_after,
            ),
            "building_consent_required": application.building_consent_required,
            "building_consent_obtained": application.building_consent_obtained,
            "contractor_quotes_obtained": application.contractor_quotes_obtained,
            "contractor_name": application.contractor_name,
            "contractor_licensed": application.contractor_licensed,
        }

    messages.info(request, f"Continuing application {application.application_id}")
    return redirect("loans:renovation_loan_application_step", step=1)


@login_required
def renovation_loan_application_step(request, step):
    """Handle multi-step renovation loan application"""
    partner = get_partner(request.user)

    forms = [BaseApplicationForm, RenovationApplicationForm]

    if step < 1 or step > len(forms):
        return redirect("loans:renovation_loan_application_start")

    form_class = forms[step - 1]
    session_key = f"renovation_step_{step}_data"

    if request.method == "POST":
        form = form_class(request.POST)

        if "save_draft" in request.POST:
            if form.is_valid():
                cleaned_data = _serialize_form_data(form.cleaned_data)
                request.session[session_key] = cleaned_data
                _save_renovation_draft(request, partner)
                messages.success(request, "Application saved as draft.")
                return redirect("loans:renovation_loan_application")

        elif form.is_valid():
            cleaned_data = _serialize_form_data(form.cleaned_data)
            request.session[session_key] = cleaned_data
            logger.info(
                "Partner %s completed renovation step %s",
                request.user.username,
                step,
            )

            next_step = step + 1
            if next_step > len(forms):
                return redirect("loans:renovation_loan_application_submit")
            return redirect("loans:renovation_loan_application_step", step=next_step)
    else:
        initial_data = request.session.get(session_key, {})
        form = form_class(initial=initial_data)

    context = {
        "form": form,
        "step": step,
        "total_steps": len(forms),
        "title": "Renovation Loan Application",
        "loan_type": "renovation",
    }

    return render(request, "loans/loan_application_step.html", context)


def _save_renovation_draft(request, partner):
    """Helper to save renovation application as draft"""
    from datetime import datetime

    step_1 = request.session.get("renovation_step_1_data", {})
    step_2 = request.session.get("renovation_step_2_data", {})

    if not step_1:
        return None

    dob_str = step_1.get("customer_date_of_birth")
    if isinstance(dob_str, str):
        dob = datetime.fromisoformat(dob_str).date()
    else:
        dob = dob_str

    app_id = request.session.get("renovation_application_id")
    if app_id:
        try:
            application = RenovationLoanApplication.objects.get(
                id=app_id,
                partner=partner,
            )
        except RenovationLoanApplication.DoesNotExist:
            application = RenovationLoanApplication(partner=partner)
    else:
        application = RenovationLoanApplication(partner=partner)

    for field, value in step_1.items():
        if field == "customer_date_of_birth":
            setattr(application, field, dob)
        elif value != "" and value is not None:
            setattr(application, field, value)

    for field, value in step_2.items():
        if value != "" and value is not None:
            setattr(application, field, value)

    application.save()
    request.session["renovation_application_id"] = str(application.id)

    return application


@login_required
def renovation_loan_application_submit(request):
    """Final submission of renovation loan application"""
    partner = get_partner(request.user)

    application = _save_renovation_draft(request, partner)

    if not application:
        messages.error(request, "No application data found. Please start again.")
        return redirect("loans:renovation_loan_application_start")

    application.status = "submitted"
    application.submitted_at = timezone.now()
    application.save()

    logger.info(
        "Renovation loan application %s submitted by %s",
        application.application_id,
        request.user.username,
    )

    for key in list(request.session.keys()):
        if key.startswith("renovation_"):
            del request.session[key]

    messages.success(
        request,
        "Renovation loan application submitted successfully! Reference: ",
        application.application_id,
    )
    return redirect("loans:renovation_loan_application")


# ==================== DEPOSIT LOAN VIEWS ====================


@login_required
def deposit_loan_application(request):
    """Landing page for deposit loans"""
    partner = get_partner(request.user)

    draft_applications = DepositLoanApplication.objects.filter(
        partner=partner,
        status="draft",
    ).order_by("-updated_at")[:10]

    retrieval_form = ApplicationRetrievalForm()

    if request.method == "POST" and "retrieve_application" in request.POST:
        retrieval_form = ApplicationRetrievalForm(request.POST)
        if retrieval_form.is_valid():
            email = retrieval_form.cleaned_data["customer_email"]
            dob = retrieval_form.cleaned_data["customer_date_of_birth"]

            applications = DepositLoanApplication.find_application(email, dob)
            applications = applications.filter(partner=partner, status="draft")

            if applications.exists():
                app = applications.first()
                return redirect("loans:deposit_loan_application_continue", pk=app.id)
            messages.warning(request, "No draft application found with those details.")

    context = {
        "partner": partner,
        "draft_applications": draft_applications,
        "retrieval_form": retrieval_form,
    }

    return render(request, "loans/deposit_loan_application.html", context)


@login_required
def deposit_loan_application_start(request):
    """Start a new deposit loan application"""
    for key in list(request.session.keys()):
        if key.startswith("deposit_"):
            del request.session[key]

    return redirect("loans:deposit_loan_application_step", step=1)


@login_required
def deposit_loan_application_continue(request, pk):
    """Continue an existing draft deposit application"""
    partner = get_partner(request.user)
    application = get_object_or_404(
        DepositLoanApplication,
        id=pk,
        partner=partner,
        status="draft",
    )

    request.session["deposit_application_id"] = str(application.id)

    # Populate step 1 data (base fields) - INCLUDING NEW NZ FIELDS
    request.session["deposit_step_1_data"] = {
        "customer_email": application.customer_email,
        "customer_date_of_birth": application.customer_date_of_birth.isoformat(),
        "first_name": application.first_name,
        "last_name": application.last_name,
        "phone_number": application.phone_number,
        "street_address": application.street_address,
        "suburb": application.suburb,
        "city": application.city,
        "postcode": application.postcode,
        "region": application.region,
        "annual_income": str(application.annual_income),
        "employment_status": application.employment_status,
        "employer_name": application.employer_name,
        "ird_number": application.ird_number or "",
        "loan_amount": str(application.loan_amount),
        "loan_purpose": application.loan_purpose,
    }

    # Populate step 2 data (deposit-specific) - INCLUDING NEW NZ FIELDS
    if application.property_address or application.property_city:
        request.session["deposit_step_2_data"] = {
            "property_address": application.property_address or "",
            "property_suburb": application.property_suburb or "",
            "property_city": application.property_city,
            "property_postcode": application.property_postcode or "",
            "property_region": application.property_region,
            "property_type": application.property_type,
            "purchase_price": str(application.purchase_price),
            "deposit_amount_required": str(application.deposit_amount_required),
            "is_first_home_buyer": application.is_first_home_buyer,
            "first_home_grant_approved": application.first_home_grant_approved,
            "first_home_loan_approved": application.first_home_loan_approved,
            "property_identified": application.property_identified,
            "has_existing_mortgage": application.has_existing_mortgage,
            "existing_mortgage_balance": str(application.existing_mortgage_balance)
            if application.existing_mortgage_balance
            else "",
            "mortgage_pre_approval": application.mortgage_pre_approval,
            "mortgage_pre_approval_amount": str(
                application.mortgage_pre_approval_amount,
            )
            if application.mortgage_pre_approval_amount
            else "",
            "kiwisaver_withdrawal_amount": str(application.kiwisaver_withdrawal_amount)
            if application.kiwisaver_withdrawal_amount
            else "",
            "other_deposit_sources": application.other_deposit_sources,
        }

    messages.info(request, f"Continuing application {application.application_id}")
    return redirect("loans:deposit_loan_application_step", step=1)


@login_required
def deposit_loan_application_step(request, step):
    """Handle multi-step deposit loan application"""
    partner = get_partner(request.user)

    forms = [BaseApplicationForm, DepositApplicationForm]

    if step < 1 or step > len(forms):
        return redirect("loans:deposit_loan_application_start")

    form_class = forms[step - 1]
    session_key = f"deposit_step_{step}_data"

    if request.method == "POST":
        form = form_class(request.POST)

        if "save_draft" in request.POST:
            if form.is_valid():
                cleaned_data = _serialize_form_data(form.cleaned_data)
                request.session[session_key] = cleaned_data
                _save_deposit_draft(request, partner)
                messages.success(request, "Application saved as draft.")
                return redirect("loans:deposit_loan_application")

        elif form.is_valid():
            cleaned_data = _serialize_form_data(form.cleaned_data)
            request.session[session_key] = cleaned_data
            logger.info(
                "Partner %s completed deposit step %s",
                request.user.username,
                step,
            )

            next_step = step + 1
            if next_step > len(forms):
                return redirect("loans:deposit_loan_application_submit")
            return redirect("loans:deposit_loan_application_step", step=next_step)
    else:
        initial_data = request.session.get(session_key, {})
        form = form_class(initial=initial_data)

    context = {
        "form": form,
        "step": step,
        "total_steps": len(forms),
        "title": "Deposit Loan Application",
        "loan_type": "deposit",
    }

    return render(request, "loans/loan_application_step.html", context)


def _save_deposit_draft(request, partner):
    """Helper to save deposit application as draft"""
    from datetime import datetime

    step_1 = request.session.get("deposit_step_1_data", {})
    step_2 = request.session.get("deposit_step_2_data", {})

    if not step_1:
        return None

    dob_str = step_1.get("customer_date_of_birth")
    if isinstance(dob_str, str):
        dob = datetime.fromisoformat(dob_str).date()
    else:
        dob = dob_str

    app_id = request.session.get("deposit_application_id")
    if app_id:
        try:
            application = DepositLoanApplication.objects.get(id=app_id, partner=partner)
        except DepositLoanApplication.DoesNotExist:
            application = DepositLoanApplication(partner=partner)
    else:
        application = DepositLoanApplication(partner=partner)

    for field, value in step_1.items():
        if field == "customer_date_of_birth":
            setattr(application, field, dob)
        elif value != "" and value is not None:
            setattr(application, field, value)

    for field, value in step_2.items():
        if value != "" and value is not None:
            setattr(application, field, value)

    application.save()
    request.session["deposit_application_id"] = str(application.id)

    return application


@login_required
def deposit_loan_application_submit(request):
    """Final submission of deposit loan application"""
    partner = get_partner(request.user)

    application = _save_deposit_draft(request, partner)

    if not application:
        messages.error(request, "No application data found. Please start again.")
        return redirect("loans:deposit_loan_application_start")

    application.status = "submitted"
    application.submitted_at = timezone.now()
    application.save()

    logger.info(
        "Deposit loan application %s submitted by %s",
        application.application_id,
        request.user.username,
    )

    for key in list(request.session.keys()):
        if key.startswith("deposit_"):
            del request.session[key]

    messages.success(
        request,
        "Deposit loan application submitted successfully! Reference: %s",
        application.application_id,
    )
    return redirect("loans:deposit_loan_application")


# ==================== APPLICATION MANAGEMENT VIEWS ====================


@login_required
def application_detail(request, loan_type, pk):
    """View details of a specific application"""
    partner = get_partner(request.user)

    model_map = {
        "marketing": MarketingLoanApplication,
        "renovation": RenovationLoanApplication,
        "deposit": DepositLoanApplication,
    }

    model = model_map.get(loan_type)
    if not model:
        messages.error(request, "Invalid loan type.")
        return redirect("loans:all_loan_applications")

    application = get_object_or_404(model, id=pk, partner=partner)

    context = {
        "application": application,
        "loan_type": loan_type,
        "partner": partner,
    }

    return render(request, "loans/application_detail.html", context)


@login_required
def partner_applications_list(request, loan_type=None):
    """List all applications for a partner, optionally filtered by loan type"""
    partner = get_partner(request.user)

    # Get filter parameters
    status_filter = request.GET.get("status", "")

    if loan_type == "marketing":
        applications = MarketingLoanApplication.objects.filter(partner=partner)
        title = "Marketing Loan Applications"
    elif loan_type == "renovation":
        applications = RenovationLoanApplication.objects.filter(partner=partner)
        title = "Renovation Loan Applications"
    elif loan_type == "deposit":
        applications = DepositLoanApplication.objects.filter(partner=partner)
        title = "Deposit Loan Applications"
    else:
        # Show all applications
        marketing = MarketingLoanApplication.objects.filter(partner=partner)
        renovation = RenovationLoanApplication.objects.filter(partner=partner)
        deposit = DepositLoanApplication.objects.filter(partner=partner)

        if status_filter:
            marketing = marketing.filter(status=status_filter)
            renovation = renovation.filter(status=status_filter)
            deposit = deposit.filter(status=status_filter)

        context = {
            "marketing_applications": marketing.order_by("-updated_at"),
            "renovation_applications": renovation.order_by("-updated_at"),
            "deposit_applications": deposit.order_by("-updated_at"),
            "partner": partner,
            "title": "All Loan Applications",
            "status_filter": status_filter,
        }

        return render(request, "loans/all_applications_list.html", context)

    if status_filter:
        applications = applications.filter(status=status_filter)

    applications = applications.order_by("-updated_at")

    context = {
        "applications": applications,
        "partner": partner,
        "loan_type": loan_type,
        "title": title,
        "status_filter": status_filter,
    }

    return render(request, "loans/applications_list.html", context)
