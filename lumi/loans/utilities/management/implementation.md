# Field-Level Encryption Implementation Guide

## Overview

This guide explains how to implement field-level encryption for sensitive loan application data using Fernet symmetric encryption.

## What's Been Encrypted

### Encrypted Fields (High Sensitivity):
- ✅ **IRD Number** - Tax identification
- ✅ **Date of Birth** - Personal identifier
- ✅ **NZBN** - Business identification (Marketing loans only)

### NOT Encrypted (Queryable Data):
- ❌ Names, addresses, email
- ❌ Loan amounts, financial data
- ❌ Application status, timestamps
- ❌ Property information

**Why this approach?** Balance security with performance. We encrypt the minimum necessary fields to protect identity while keeping the application queryable.

---

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install cryptography
```

Add to your `requirements.txt`:
```
cryptography>=41.0.0
```

### Step 2: File Structure

Create these files in your Django app:

```
lumi/loans/
├── models.py                  # Updated models (provided)
├── encryption.py              # Encryption utilities (provided)
└── management/
    └── commands/
        ├── __init__.py
        ├── generate_encryption_key.py      # Key generation command
        └── migrate_encrypt_data.py         # Data migration command
```

**Copy the files I created to these locations:**
- `models.py` → `lumi/loans/models.py`
- `encryption.py` → `lumi/loans/encryption.py`
- `management_command_generate_encryption_key.py` → `lumi/loans/management/commands/generate_encryption_key.py`
- `management_command_migrate_encrypt_data.py` → `lumi/loans/management/commands/migrate_encrypt_data.py`

### Step 3: Generate Encryption Key

```bash
python manage.py generate_encryption_key
```

This will output something like:
```
FIELD_ENCRYPTION_KEY = "xNjdG4yOHpwTjR6NWE4cTN5bXZoZjJrOGRnNXN3Yzg9"
```

### Step 4: Store the Key Securely

**Option A: Environment Variables (Recommended for Production)**

Create/update `.env` file:
```bash
FIELD_ENCRYPTION_KEY=xNjdG4yOHpwTjR6NWE4cTN5bXZoZjJrOGRnNXN3Yzg9
```

In `settings.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

FIELD_ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY')
```

**Option B: Django Settings (Development Only)**

In `settings.py`:
```python
# NEVER commit this to version control in production!
FIELD_ENCRYPTION_KEY = "xNjdG4yOHpwTjR6NWE4cTN5bXZoZjJrOGRnNXN3Yzg9"
```

**Option C: AWS Secrets Manager / Azure Key Vault (Production)**

```python
import boto3
from botocore.exceptions import ClientError

def get_secret():
    secret_name = "loan_app_encryption_key"
    region_name = "ap-southeast-2"  # Sydney region

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e

FIELD_ENCRYPTION_KEY = get_secret()
```

### Step 5: Create Database Migration

```bash
python manage.py makemigrations
```

This creates a migration to add the encrypted fields:
- `_encrypted_customer_dob`
- `_encrypted_ird_number`
- `_encrypted_nzbn`

Review the migration, then apply it:

```bash
python manage.py migrate
```

### Step 6: Encrypt Existing Data (If Any)

**Test first with dry run:**
```bash
python manage.py migrate_encrypt_data --dry-run
```

**Then encrypt for real:**
```bash
python manage.py migrate_encrypt_data
```

---

## How to Use in Your Code

### Creating New Applications

The encrypted fields work transparently through properties:

```python
from datetime import date
from lumi.loans.models import MarketingLoanApplication

# Create application - use fields normally
application = MarketingLoanApplication(
    partner=partner,
    customer_email="john@example.com",
    customer_date_of_birth=date(1985, 6, 15),  # Automatically encrypted
    ird_number="123456789",                     # Automatically encrypted
    nzbn="1234567890123",                       # Automatically encrypted
    first_name="John",
    last_name="Smith",
    # ... other fields
)
application.save()
```

### Reading Encrypted Fields

Access through properties - decryption is automatic:

```python
# Retrieve application
app = MarketingLoanApplication.objects.get(application_id=some_uuid)

# Access encrypted fields normally
print(app.customer_date_of_birth)  # Automatically decrypted: 1985-06-15
print(app.ird_number)               # Automatically decrypted: "123456789"
print(app.nzbn)                     # Automatically decrypted: "1234567890123"

# The encrypted values are in private fields
print(app._encrypted_customer_dob)  # bytes: b'gAAAAABh...'
```

### Updating Encrypted Fields

```python
app = MarketingLoanApplication.objects.get(application_id=some_uuid)

# Update encrypted field
app.ird_number = "987654321"  # Automatically re-encrypted
app.save()
```

### Querying Applications

**Email queries work normally:**
```python
# This works - email is not encrypted
apps = MarketingLoanApplication.objects.filter(
    customer_email="john@example.com"
)
```

**Date of birth queries require special handling:**
```python
# Use the helper method (filters by email first, then DOB in Python)
apps = MarketingLoanApplication.find_application(
    email="john@example.com",
    date_of_birth=date(1985, 6, 15)
)

# Or filter by email then check DOB manually
apps = MarketingLoanApplication.objects.filter(customer_email="john@example.com")
for app in apps:
    if app.customer_date_of_birth == date(1985, 6, 15):
        # Found it!
        process_application(app)
```

### Django Admin

The fields will appear normally in forms since they use properties:

```python
# admin.py
from django.contrib import admin
from .models import MarketingLoanApplication

@admin.register(MarketingLoanApplication)
class MarketingLoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_id', 'first_name', 'last_name', 'customer_email', 'status']

    # Encrypted fields work in forms automatically
    fields = [
        'partner',
        'customer_email',
        'customer_date_of_birth',  # Shows decrypted value
        'ird_number',              # Shows decrypted value
        'nzbn',                    # Shows decrypted value
        # ... other fields
    ]

    # Don't show the _encrypted_* fields in admin
    exclude = ['_encrypted_customer_dob', '_encrypted_ird_number', '_encrypted_nzbn']
```

### Serializers (Django REST Framework)

```python
from rest_framework import serializers
from .models import MarketingLoanApplication

class MarketingLoanApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingLoanApplication
        fields = [
            'application_id',
            'customer_email',
            'customer_date_of_birth',  # Handled by property
            'ird_number',              # Handled by property
            'nzbn',                    # Handled by property
            # ... other fields
        ]
        # Exclude the raw encrypted fields
        extra_kwargs = {
            '_encrypted_customer_dob': {'write_only': True},
            '_encrypted_ird_number': {'write_only': True},
            '_encrypted_nzbn': {'write_only': True},
        }
```

---

## Security Best Practices

### 1. Key Management

✅ **DO:**
- Store key in environment variables
- Use secrets management (AWS Secrets Manager, Azure Key Vault)
- Rotate keys periodically (requires re-encryption migration)
- Backup the key securely (separate from database backups)
- Use different keys for dev/staging/production

❌ **DON'T:**
- Commit keys to version control
- Store keys in database
- Hardcode keys in source code
- Share keys via email/Slack
- Store keys in container images

### 2. Access Control

```python
# Limit who can view sensitive fields
class LoanApplicationViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.request.user.has_perm('loans.view_sensitive_data'):
            return FullLoanApplicationSerializer
        return LimitedLoanApplicationSerializer  # Excludes IRD, DOB
```

### 3. Audit Logging

```python
# Log access to encrypted fields
import logging
from django.db.models.signals import post_init

logger = logging.getLogger('security')

def log_sensitive_access(sender, instance, **kwargs):
    if instance._state.adding:
        return

    # Track when encrypted fields are accessed
    original_getattr = instance.__getattribute__

    def tracking_getattr(name):
        if name in ['customer_date_of_birth', 'ird_number', 'nzbn']:
            logger.info(
                f"Sensitive field accessed: {name} "
                f"on {instance.application_id} "
                f"by {get_current_user()}"
            )
        return original_getattr(name)

    instance.__getattribute__ = tracking_getattr

post_init.connect(log_sensitive_access, sender=MarketingLoanApplication)
```

### 4. Database-Level Security

- Enable database encryption at rest
- Use encrypted database backups
- Enable TLS/SSL for database connections
- Implement role-based access control (RBAC)

---

## Performance Considerations

### Encryption Overhead

- **Fernet encryption:** ~0.1-0.5ms per field
- **Impact:** Minimal for typical operations (<100 records)
- **Bulk operations:** Use select_related/prefetch_related as normal

### Optimization Tips

**1. Batch decryption:**
```python
# This is fine - Python properties cache values
apps = MarketingLoanApplication.objects.all()[:100]
for app in apps:
    print(app.ird_number)  # Only decrypts once per instance
```

**2. Avoid unnecessary decryption:**
```python
# Good: Only decrypt when needed
if should_show_sensitive_data(user):
    ird = application.ird_number

# Bad: Always decrypting
ird = application.ird_number or "N/A"
```

**3. Use defer() for large querysets:**
```python
# Don't load encrypted fields unless needed
apps = MarketingLoanApplication.objects.defer(
    '_encrypted_customer_dob',
    '_encrypted_ird_number'
).filter(status='approved')
```

---

## Testing

### Unit Tests

```python
from django.test import TestCase
from datetime import date
from lumi.loans.models import MarketingLoanApplication

class EncryptionTestCase(TestCase):
    def test_ird_encryption(self):
        """Test IRD number is encrypted and decrypted correctly"""
        app = MarketingLoanApplication.objects.create(
            partner=self.partner,
            ird_number="123456789",
            # ... other required fields
        )

        # Check it's encrypted in database
        self.assertIsNotNone(app._encrypted_ird_number)
        self.assertIsInstance(app._encrypted_ird_number, bytes)

        # Check it decrypts correctly
        self.assertEqual(app.ird_number, "123456789")

        # Reload from database
        app_reloaded = MarketingLoanApplication.objects.get(pk=app.pk)
        self.assertEqual(app_reloaded.ird_number, "123456789")

    def test_dob_encryption(self):
        """Test date of birth is encrypted and decrypted correctly"""
        dob = date(1985, 6, 15)
        app = MarketingLoanApplication.objects.create(
            partner=self.partner,
            customer_date_of_birth=dob,
            # ... other required fields
        )

        # Check it's encrypted
        self.assertIsNotNone(app._encrypted_customer_dob)

        # Check it decrypts correctly
        self.assertEqual(app.customer_date_of_birth, dob)

    def test_find_application_with_encrypted_dob(self):
        """Test finding applications by email and encrypted DOB"""
        dob = date(1985, 6, 15)
        email = "test@example.com"

        app = MarketingLoanApplication.objects.create(
            partner=self.partner,
            customer_email=email,
            customer_date_of_birth=dob,
            # ... other required fields
        )

        # Use the find_application helper
        found = MarketingLoanApplication.find_application(email, dob)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].application_id, app.application_id)
```

---

## Troubleshooting

### Problem: "FIELD_ENCRYPTION_KEY not found in settings"

**Solution:** Make sure you've added the key to settings or environment variables.

```python
# In settings.py
FIELD_ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY')

# Verify it's loaded
print(f"Key loaded: {bool(FIELD_ENCRYPTION_KEY)}")
```

### Problem: "Decryption error" in logs

**Causes:**
- Wrong encryption key
- Corrupted data
- Data encrypted with different key

**Solution:**
```python
# Test with a known value
from lumi.loans.encryption import encrypt_field, decrypt_field

test = "test123"
encrypted = encrypt_field(test)
decrypted = decrypt_field(encrypted)
print(f"Success: {decrypted == test}")
```

### Problem: Can't query by date of birth

**Expected:** You can't directly query encrypted fields in the database.

**Solution:** Use the `find_application()` helper method or filter by email first, then check DOB in Python.

### Problem: Migrations failing

**Solution:** Ensure you've:
1. Generated the encryption key
2. Added it to settings
3. Run `makemigrations` before `migrate`

---

## Migration from Unencrypted Data

If you already have data in production:

```bash
# 1. Deploy new code (with encryption support)
git pull
pip install -r requirements.txt

# 2. Add encryption key to environment
export FIELD_ENCRYPTION_KEY="your-key-here"

# 3. Run migrations (adds encrypted columns)
python manage.py migrate

# 4. Encrypt existing data (dry run first!)
python manage.py migrate_encrypt_data --dry-run

# 5. Encrypt for real
python manage.py migrate_encrypt_data

# 6. Verify in Django shell
python manage.py shell
>>> from lumi.loans.models import MarketingLoanApplication
>>> app = MarketingLoanApplication.objects.first()
>>> print(app.ird_number)  # Should print decrypted value
>>> print(app._encrypted_ird_number)  # Should print bytes
```

---

## Key Rotation (Advanced)

To rotate encryption keys:

1. Generate new key
2. Create migration script that:
   - Decrypts with old key
   - Re-encrypts with new key
3. Update all environments with new key

```python
# Example rotation script
from django.core.management.base import BaseCommand
from cryptography.fernet import Fernet

class Command(BaseCommand):
    def handle(self, *args, **options):
        OLD_KEY = os.environ['OLD_ENCRYPTION_KEY']
        NEW_KEY = os.environ['NEW_ENCRYPTION_KEY']

        old_fernet = Fernet(OLD_KEY)
        new_fernet = Fernet(NEW_KEY)

        for app in MarketingLoanApplication.objects.all():
            if app._encrypted_ird_number:
                # Decrypt with old key
                decrypted = old_fernet.decrypt(app._encrypted_ird_number)
                # Re-encrypt with new key
                app._encrypted_ird_number = new_fernet.encrypt(decrypted)
                app.save()
```

---

## Summary

✅ **What's been done:**
- IRD numbers encrypted
- Dates of birth encrypted
- NZBNs encrypted (Marketing loans)
- Transparent access through properties
- Helper methods for querying

✅ **What you need to do:**
1. Install `cryptography` package
2. Copy files to correct locations
3. Generate encryption key
4. Store key securely
5. Run migrations
6. Encrypt existing data (if any)

✅ **Result:**
- Sensitive data protected at rest
- Application remains queryable
- Minimal code changes needed
- No performance impact for typical usage

---

## Questions?

Common questions:

**Q: Can I encrypt more fields?**
A: Yes, follow the same pattern for any field. Add `_encrypted_fieldname` as BinaryField and create property getters/setters.

**Q: What about credit card numbers?**
A: DO NOT store credit card numbers. Use payment processors (Stripe, PayPal) and store tokens only.

**Q: How do I search encrypted fields?**
A: You can't directly. Filter by non-encrypted fields first (like email), then check encrypted fields in Python.

**Q: What if I lose the encryption key?**
A: Data is permanently lost. **Backup the key securely** in multiple locations.

**Q: Does this work with database backups?**
A: Yes, but keep the encryption key separate from database backups for security.
