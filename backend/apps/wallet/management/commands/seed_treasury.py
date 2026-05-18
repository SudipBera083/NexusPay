import os
from django.core.management.base import BaseCommand
from apps.wallet.models import Wallet, WalletType

class Command(BaseCommand):
    help = 'Seeds treasury wallets for double-entry system'

    def handle(self, *args, **options):
        wallets = [
            (WalletType.TREASURY_EXTERNAL, "External Banking System (Nostro)"),
            (WalletType.TREASURY_EXTERNAL_UPI, "UPI On-Ramp Treasury"),
            (WalletType.TREASURY_RESERVE_INR, "INR Reserve Treasury"),
            (WalletType.TREASURY_RESERVE_USDT, "USDT Reserve Treasury"),
            (WalletType.TREASURY_USDC_RESERVE, "USDC Reserve Treasury"),
            (WalletType.TREASURY_SETTLEMENT, "Merchant Settlement Pool"),
            (WalletType.TREASURY_FEES, "Fee Collection Treasury"),
            (WalletType.TREASURY_BLOCKCHAIN_GAS, "Gas Reserve Treasury"),
            (WalletType.TREASURY_RISK_BUFFER, "Risk Buffer Treasury"),
        ]

        created_count = 0
        for wtype, label in wallets:
            w, created = Wallet.objects.get_or_create(
                type=wtype,
                defaults={'label': label}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created {wtype}: {label}"))
                created_count += 1
            elif w.label != label:
                w.label = label
                w.save(update_fields=['label'])
                self.stdout.write(self.style.WARNING(f"Updated {wtype}: {label}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {created_count} treasury wallets.'))
