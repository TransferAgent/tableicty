from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Issuer, Holding, Certificate
import json


class Command(BaseCommand):
    help = 'Generate TAVS (Transfer Agent Verified Shares) report for an issuer'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--issuer-id',
            type=str,
            required=True,
            help='UUID of the issuer to generate report for'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output file path (optional, defaults to stdout)'
        )
    
    def handle(self, *args, **options):
        issuer_id = options['issuer_id']
        output_file = options['output']
        
        try:
            issuer = Issuer.objects.get(id=issuer_id)
        except Issuer.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Issuer with ID {issuer_id} not found'))
            return
        
        holdings = Holding.objects.filter(issuer=issuer).select_related('shareholder', 'security_class')
        certificates = Certificate.objects.filter(issuer=issuer)
        
        total_issued = sum(h.share_quantity for h in holdings)
        total_restricted = sum(h.share_quantity for h in holdings if h.is_restricted)
        total_unrestricted = total_issued - total_restricted
        
        shareholder_count = holdings.values('shareholder').distinct().count()
        certificate_count = certificates.filter(status='OUTSTANDING').count()
        drs_count = holdings.filter(holding_type='DRS').count()
        
        report = {
            'issuer': {
                'company_name': issuer.company_name,
                'ticker_symbol': issuer.ticker_symbol,
                'cusip': issuer.cusip,
                'cik': issuer.cik,
            },
            'report_date': timezone.now().date().isoformat(),
            'shares_authorized': float(issuer.total_authorized_shares),
            'shares_issued': float(total_issued),
            'shares_outstanding': float(total_issued),
            'shares_restricted': float(total_restricted),
            'shares_unrestricted': float(total_unrestricted),
            'shareholder_count': shareholder_count,
            'shareholders_of_record': shareholder_count,
            'certificate_count': certificate_count,
            'drs_count': drs_count,
            'tavs_enabled': issuer.tavs_enabled,
            'otc_tier': issuer.otc_tier,
        }
        
        report_json = json.dumps(report, indent=2)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_json)
            self.stdout.write(self.style.SUCCESS(f'TAVS report generated: {output_file}'))
        else:
            self.stdout.write(report_json)
        
        self.stdout.write(self.style.SUCCESS(f'TAVS report generated for {issuer.company_name}'))
