"""
Management command to generate a new encryption key for field-level encryption.

Usage:
    python manage.py generate_encryption_key
"""

from cryptography.fernet import Fernet
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a new Fernet encryption key for field-level encryption"

    def handle(self, *args, **options):
        key = Fernet.generate_key().decode()

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("New Encryption Key Generated"))
        self.stdout.write(self.style.SUCCESS("=" * 70 + "\n"))

        self.stdout.write(self.style.WARNING("IMPORTANT: Store this key securely!\n"))
        self.stdout.write("Add this to your settings or environment variables:\n")
        self.stdout.write(self.style.SUCCESS(f'\nFIELD_ENCRYPTION_KEY = "{key}"\n'))

        self.stdout.write("\nFor environment variables (.env file):")
        self.stdout.write(self.style.SUCCESS(f"FIELD_ENCRYPTION_KEY={key}\n"))

        self.stdout.write(self.style.WARNING("\n" + "!" * 70))
        self.stdout.write(self.style.WARNING("DO NOT:"))
        self.stdout.write(self.style.WARNING("  - Commit this key to version control"))
        self.stdout.write(self.style.WARNING("  - Share this key in plain text"))
        self.stdout.write(
            self.style.WARNING("  - Lose this key (data will be unrecoverable)"),
        )
        self.stdout.write(self.style.WARNING("!" * 70 + "\n"))

        self.stdout.write(self.style.SUCCESS("✓ Key generation complete\n"))
