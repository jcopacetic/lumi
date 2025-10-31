# Partner App Test Implementation Guide

Complete guide to implementing 100% test coverage for your Luminate Financial Group loan portal's partner app.

## 📋 Prerequisites

Ensure these are in your `requirements/local.txt`:
```
pytest==6.2.5
pytest-django==4.5.2
pytest-mock==3.6.1
coverage==6.2
```

## 📁 File Structure

Create this structure in your partners app:

```
lumi/partners/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_models.py       # Partner model tests
│   ├── test_views.py        # View tests
│   ├── test_forms.py        # Form tests
│   └── README.md            # Test documentation
├── models.py
├── views.py
├── forms.py
└── ...
```

## 🚀 Implementation Steps

### Step 1: Create the tests directory
```bash
mkdir -p lumi/partners/tests
```

### Step 2: Copy the test files
Copy these files into `lumi/partners/tests/`:
- `__init__.py`
- `conftest.py`
- `test_models.py`
- `test_views.py`
- `test_forms.py`
- `README.md`

### Step 3: Update imports if needed
Make sure all imports match your project structure. The tests assume:
- User model: `lumi.users.models.User`
- Partner model: `lumi.partners.models.Partner`
- Partner form: `lumi.partners.forms.PartnerSignupForm`

### Step 4: Configure pytest
Ensure your `pytest.ini` at the project root includes:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py *_tests.py
addopts = --reuse-db
```

### Step 5: Run the tests
```bash
# Run all partner tests
docker-compose -f local.yml run --rm django pytest lumi/partners/tests/

# With coverage
docker-compose -f local.yml run --rm django coverage run -m pytest lumi/partners/tests/
docker-compose -f local.yml run --rm django coverage report
```

## 📊 What's Covered

### Models (test_models.py)
✅ 56 tests covering:
- Partner creation and validation
- String representation
- Partner type choices (Real Estate, Family Office, Mortgage Broker)
- Email uniqueness
- Invite token generation and uniqueness
- send_invite() method with success and failure cases
- get_invite_url() method
- regenerate_invite_token() with and without save
- is_invite_expired() with various scenarios
- mark_as_accepted() method
- has_accepted property (all edge cases)
- invite_status property (Accepted, Expired, Pending)
- One-to-one User relationship
- Cascade delete behavior
- Auto-timestamp fields (invited_at, created_at, updated_at)

### Views (test_views.py)
✅ 22 tests covering:

**PartnerSignupView:**
- Missing token validation
- Invalid token validation
- Already accepted token
- Expired token
- Valid token flow
- Email pre-fill in form
- User linking on signup
- Context data

**PartnerDashboardView:**
- User without partner profile
- Inactive partner (403 response)
- Active partner access
- Login requirement
- Context data

**validate_partner_token:**
- Missing token parameter
- Invalid token
- Already accepted invitation
- Expired invitation
- Valid token (session storage)

**resend_partner_invite:**
- Non-staff user (403)
- Non-existent partner (404)
- Already accepted partner warning
- Successful resend with token regeneration
- Exception handling

### Forms (test_forms.py)
✅ 11 tests covering:
- Form fields presence
- Valid data submission
- Email validation (required, format, uniqueness)
- Password validation (required, mismatch, too short)
- Initial email pre-fill
- Inheritance from allauth SignupForm

## 🔍 Checking Coverage

### Generate coverage report
```bash
docker-compose -f local.yml run --rm django coverage run -m pytest lumi/partners/tests/
docker-compose -f local.yml run --rm django coverage report --include="lumi/partners/*"
```

### Generate HTML coverage report
```bash
docker-compose -f local.yml run --rm django coverage html --include="lumi/partners/*"
# Open htmlcov/index.html in your browser
```

### Expected output
```
Name                              Stmts   Miss  Cover
-----------------------------------------------------
lumi/partners/__init__.py             0      0   100%
lumi/partners/models.py              87      0   100%
lumi/partners/views.py               65      0   100%
lumi/partners/forms.py               12      0   100%
-----------------------------------------------------
TOTAL                               164      0   100%
```

## 🛠️ Customization Needed

You may need to adjust these based on your actual implementation:

### 1. URL names
The tests assume these URL names exist:
- `account_login`
- `account_signup`
- `partners:partner_signup`
- `partners:dashboard`

Update in `test_views.py` if your URLs differ.

### 2. Settings
Tests assume these settings exist:
- `settings.SITE_URL`
- `settings.DEFAULT_FROM_EMAIL`

### 3. Email template
Tests assume `templates/emails/partner_invite.txt` exists.

### 4. Partner model fields
If you add/remove fields from Partner model, update:
- Fixtures in `conftest.py`
- Model tests in `test_models.py`

## 🧪 Test Workflow

### For New Features
1. **Write the test first** (TDD)
2. **Run the test** (it should fail)
3. **Implement the feature**
4. **Run the test again** (it should pass)
5. **Check coverage**

### For Bug Fixes
1. **Write a test that reproduces the bug**
2. **Verify the test fails**
3. **Fix the bug**
4. **Verify the test passes**
5. **Commit both fix and test**

## 📈 Maintaining 100% Coverage

### Before committing code:
```bash
# Run tests
docker-compose -f local.yml run --rm django pytest lumi/partners/tests/

# Check coverage
docker-compose -f local.yml run --rm django coverage run -m pytest lumi/partners/tests/
docker-compose -f local.yml run --rm django coverage report

# Should show 100% for all partners files
```

### Set up pre-commit hook (optional):
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
docker-compose -f local.yml run --rm django coverage run -m pytest lumi/partners/tests/
docker-compose -f local.yml run --rm django coverage report --fail-under=100 --include="lumi/partners/*"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## 🐛 Troubleshooting

### Tests fail with "No such table"
Run migrations:
```bash
docker-compose -f local.yml run --rm django python manage.py migrate
```

### Tests fail with import errors
Check that:
1. You're running from project root
2. `__init__.py` exists in the tests directory
3. Import paths match your project structure

### Mocking issues
If `mocker` fixture is not found, ensure `pytest-mock` is installed:
```bash
pip install pytest-mock
```

### Email sending fails in tests
This is expected. Tests use Django's `locmem` email backend. Emails are stored in `mail.outbox`, not actually sent.

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-Django Documentation](https://pytest-django.readthedocs.io/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Cookiecutter Django Testing](https://cookiecutter-django.readthedocs.io/en/latest/testing.html)

## ✅ Checklist

- [ ] Created `lumi/partners/tests/` directory
- [ ] Added all test files
- [ ] Installed test dependencies
- [ ] Ran tests successfully
- [ ] Checked coverage (should be 100%)
- [ ] Reviewed any failing tests
- [ ] Updated URL names if needed
- [ ] Updated settings references if needed
- [ ] Committed tests to version control

## 🎯 Next Steps

After implementing these tests:

1. **Test other apps** - Apply the same pattern to other apps in your project
2. **Add integration tests** - Test the full user flow end-to-end
3. **Add admin tests** - Test Django admin customizations
4. **Add API tests** - If you have API endpoints
5. **Set up CI/CD** - Run tests automatically on commits

## 💡 Tips for Success

- **Run tests frequently** - After every change
- **Keep tests simple** - One concept per test
- **Use descriptive names** - Test names should explain what they test
- **Test edge cases** - Not just happy paths
- **Mock external services** - Don't actually send emails, make API calls, etc.
- **Use fixtures** - DRY principle applies to tests too
- **Document complex tests** - Add comments explaining why, not what

---

**Questions or issues?** Open an issue or ask in your team chat!
