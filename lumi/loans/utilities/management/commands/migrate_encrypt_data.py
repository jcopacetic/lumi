"""
Data migration to encrypt existing sensitive fields.

This migration should be run AFTER:
1. Adding the encryption fields to your models
2. Running makemigrations and migrate
3. Setting up FIELD_ENCRYPTION_KEY in settings

Usage:
    python manage.py migrate_encrypt_data

This script:
- Encrypts existing IRD numbers
- Encrypts existing dates of birth
- Encrypts existing NZBNs (for Marketing applications)
- Keeps the data accessible through the property getters/setters
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from lumi.loans.models import DepositLoanApplication
from lumi.loans.models import MarketingLoanApplication
from lumi.loans.models import RenovationLoanApplication


class Command(BaseCommand):
    help = "Encrypt existing sensitive data in loan applications"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be encrypted without actually doing it",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN MODE ===\n"))

        total_encrypted = 0

        # Process each model type
        models_to_process = [
            ("Marketing", MarketingLoanApplication),
            ("Renovation", RenovationLoanApplication),
            ("Deposit", DepositLoanApplication),
        ]

        for model_name, model in models_to_process:
            self.stdout.write(f"\nProcessing {model_name} Loan Applications...")
            count = self.encrypt_model_data(model, dry_run)
            total_encrypted += count
            self.stdout.write(self.style.SUCCESS(f"  ✓ {count} records processed"))

        self.stdout.write("\n" + "=" * 70)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would encrypt {total_encrypted} records",
                ),
            )
            self.stdout.write("Run without --dry-run to actually encrypt data")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Successfully encrypted {total_encrypted} records",
                ),
            )
        self.stdout.write("=" * 70 + "\n")

    @transaction.atomic
    def encrypt_model_data(self, model, dry_run=False):
        """Encrypt sensitive fields for a specific model"""
        count = 0

        # Get all applications - we need to process all since we can't
        # query encrypted fields to see which need encryption
        applications = model.objects.all()

        for app in applications:
            needs_save = False

            # Note: The property setters will handle the encryption
            # We just need to trigger them by accessing the properties

            # Encrypt IRD number if it exists and isn't already encrypted
            if hasattr(app, "ird_number"):
                # Access through property will auto-encrypt if needed
                ird = app.ird_number
                if ird and not app._encrypted_ird_number:  # noqa: SLF001
                    app.ird_number = ird  # This triggers encryption
                    needs_save = True

            # Encrypt date of birth if it exists and isn't already encrypted
            if hasattr(app, "customer_date_of_birth"):
                dob = app.customer_date_of_birth
                if dob and not app._encrypted_customer_dob:  # noqa: SLF001
                    app.customer_date_of_birth = dob  # This triggers encryption
                    needs_save = True

            # Encrypt NZBN for Marketing applications
            if isinstance(app, MarketingLoanApplication) and hasattr(app, "nzbn"):
                nzbn = app.nzbn
                if nzbn and not app._encrypted_nzbn:  # noqa: SLF001
                    app.nzbn = nzbn  # This triggers encryption
                    needs_save = True

            if needs_save:
                if not dry_run:
                    app.save()
                count += 1

        return count
