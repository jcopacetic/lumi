# Partner App Tests

Comprehensive test suite for the `partners` app with 100% code coverage.

## Test Files

- **`test_models.py`** - Tests for Partner model (56 tests)
  - Model creation and validation
  - Email and token uniqueness
  - Invitation methods (send_invite, regenerate_invite_token)
  - Expiry logic
  - User relationship (one-to-one)
  - Properties (has_accepted, invite_status)
  - Timestamps

- **`test_views.py`** - Tests for partner views (22 tests)
  - PartnerSignupView (token validation, form handling)
  - PartnerDashboardView (authentication, authorization)
  - validate_partner_token function
  - resend_partner_invite function

- **`test_forms.py`** - Tests for PartnerSignupForm (11 tests)
  - Form field validation
  - Email validation
  - Password validation
  - Duplicate email handling
  - Initial data handling

- **`conftest.py`** - Shared fixtures
  - user, staff_user
  - partner, partner_with_user, partner_inactive, partner_expired
  - RequestFactory

## Running Tests

### Run all partner tests
```bash
docker-compose -f local.yml run --rm django pytest lumi/partners/tests/
```

### Run specific test file
```bash
docker-compose -f local.yml run --rm django pytest lumi/partners/tests/test_models.py
```

### Run specific test class
```bash
docker-compose -f local.yml run --rm django pytest lumi/partners/tests/test_models.py::TestPartnerModel
```

### Run specific test
```bash
docker-compose -f local.yml run --rm django pytest lumi/partners/tests/test_models.py::TestPartnerModel::test_partner_creation
```

### Run with coverage
```bash
docker-compose -f local.yml run --rm django coverage run -m pytest lumi/partners/tests/
docker-compose -f local.yml run --rm django coverage report
```

### Generate HTML coverage report
```bash
docker-compose -f local.yml run --rm django coverage run -m pytest lumi/partners/tests/
docker-compose -f local.yml run --rm django coverage html
# Open htmlcov/index.html in your browser
```

### Run with verbose output
```bash
docker-compose -f local.yml run --rm django pytest lumi/partners/tests/ -v
```

### Run with print statements visible
```bash
docker-compose -f local.yml run --rm django pytest lumi/partners/tests/ -s
```

## Test Requirements

Make sure these packages are installed (should be in your requirements/local.txt):
- pytest
- pytest-django
- pytest-mock (for mocking)
- coverage

## Writing New Tests

When adding new features to the partners app:

1. **Write tests first** (TDD approach) or **immediately after** implementing the feature
2. **Run coverage** to ensure all new code is tested
3. **Follow the existing patterns** in the test files
4. **Use fixtures** from conftest.py when possible
5. **Test both success and failure paths**

### Example Test Pattern

```python
class TestMyNewFeature:
    """Tests for my new feature"""

    def test_success_case(self, partner):
        """Test the happy path"""
        result = partner.my_new_method()
        assert result == expected_value

    def test_failure_case(self, partner):
        """Test error handling"""
        with pytest.raises(ExpectedException):
            partner.my_method_with_invalid_input()
```

## Coverage Goals

- **Target: 100% coverage** for the partners app
- Check coverage after each change: `coverage report`
- Review uncovered lines: `coverage html` and open htmlcov/index.html

## Common Issues

### Issue: Tests fail due to missing migrations
**Solution:** Run migrations before testing
```bash
docker-compose -f local.yml run --rm django python manage.py migrate
```

### Issue: "No module named 'lumi'"
**Solution:** Ensure you're running tests from the project root directory

### Issue: Email not being sent in tests
**Solution:** This is expected. Tests use Django's email backend which stores emails in `mail.outbox` instead of actually sending them.

### Issue: Database errors
**Solution:** Use the `db` fixture or `pytestmark = pytest.mark.django_db`

## Tips

- **Use `-x` flag** to stop on first failure: `pytest -x`
- **Use `-k` flag** to run tests matching a pattern: `pytest -k "test_invite"`
- **Use `--pdb` flag** to drop into debugger on failure: `pytest --pdb`
- **Use `-vv` flag** for extra verbose output: `pytest -vv`
