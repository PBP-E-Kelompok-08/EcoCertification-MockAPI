from django.core.management.base import BaseCommand

from main.models import Product, ProductVerification, Seller, VerificationPartner
from main.views import sync_data_from_files


class Command(BaseCommand):
    help = "Add missing seed records from data/ without overwriting live records."

    def handle(self, *args, **options):
        sync_data_from_files()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully synced data: "
                f"{Seller.objects.count()} sellers, "
                f"{VerificationPartner.objects.count()} verification partners, "
                f"{Product.objects.count()} products, "
                f"{ProductVerification.objects.count()} verifications."
            )
        )

