# Partner Invitation System - Setup Guide

## URL Configuration

### 1. Main project urls.py
Add the partners app URLs to your main project urls.py:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # allauth URLs
    path('partners/', include('partners.urls')),  # Your partners app
]
```

### 2. Partners app urls.py
This is already created for you in `urls.py`. Copy it to your partners app folder.

The URL pattern `partners:partner_signup` expects a UUID token in the URL path:
- Example: `https://yourdomain.com/partners/signup/123e4567-e89b-12d3-a1b4-426614174000/`

## Two Approaches for Signup

### Approach A: Direct Partner Signup URL (Recommended)
This uses a custom signup view that validates the token in the URL path.

**Pros:**
- Clean URL structure
- Token validation happens before rendering signup form
- Better UX with partner context in signup page

**URL in invite email:**
```
https://yourdomain.com/partners/signup/{token}/
```

**What to use:**
- `PartnerSignupView` in views.py
- `partners:partner_signup` URL pattern

---

### Approach B: Token Validation + Standard Allauth Signup
This validates the token first, stores partner info in session, then redirects to standard allauth signup.

**Pros:**
- Uses standard allauth signup (less customization needed)
- Can reuse existing allauth templates

**URL in invite email:**
```
https://yourdomain.com/accounts/signup/?token={token}
```

**What to use:**
- `validate_partner_token` view in views.py
- Hook into allauth's signup process via signals
- Store partner_id in session

**Additional setup for Approach B:**
You'll need to create a signal handler to link the user after signup:

```python
# partners/signals.py
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import Partner

@receiver(user_signed_up)
def link_partner_on_signup(request, user, **kwargs):
    partner_id = request.session.get('partner_signup_id')
    if partner_id:
        try:
            partner = Partner.objects.get(id=partner_id)
            partner.mark_as_accepted(user)
            del request.session['partner_signup_id']
        except Partner.DoesNotExist:
            pass
```

Then in `partners/apps.py`:
```python
from django.apps import AppConfig

class PartnersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'partners'

    def ready(self):
        import partners.signals
```

---

## Which Approach Should You Use?

**Use Approach A** if:
- You want the cleanest implementation
- You're okay with a custom signup template
- Token should be part of the URL path

**Use Approach B** if:
- You want to stick with allauth's standard signup
- You prefer query parameters (?token=...)
- You don't want to customize signup templates much

## Model Update
The updated `models.py` now uses:
```python
def get_invite_url(self):
    path = reverse('partners:partner_signup', kwargs={'token': self.invite_token})
    return f"{settings.SITE_URL}{path}"
```

This generates: `https://yourdomain.com/partners/signup/{uuid}/`

---

## Settings Required

Make sure these are in your settings.py:

```python
# Site URL (you mentioned you added this)
SITE_URL = "https://yourdomain.com"  # No trailing slash

# Email settings
DEFAULT_FROM_EMAIL = "noreply@yourdomain.com"
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # or console for dev

# Allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False  # If you want email-only login
ACCOUNT_AUTHENTICATION_METHOD = 'email'
```

## Testing in Development

For local testing, use:
```python
# settings.py (development only)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SITE_URL = "http://localhost:8000"
```

Emails will print to console instead of sending.

## URL Examples

After setup, your URLs will be:

- Partner signup: `http://localhost:8000/partners/signup/{token}/`
- Partner dashboard: `http://localhost:8000/partners/dashboard/`
- Django admin: `http://localhost:8000/admin/`
- Allauth login: `http://localhost:8000/accounts/login/`

## Next Steps

1. Copy `urls.py` to your partners app
2. Copy `views.py` to your partners app
3. Copy `models.py` to your partners app (or merge with existing)
4. Copy `partner_admin.py` to your partners app as `admin.py`
5. Create `templates/emails/partner_invite.txt`
6. Run migrations: `python manage.py makemigrations && python manage.py migrate`
7. Test creating a partner in admin - invite should send automatically!
