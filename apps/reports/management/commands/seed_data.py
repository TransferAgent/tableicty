from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from decimal import Decimal
import random
from datetime import timedelta

from apps.core.models import Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer


class Command(BaseCommand):
    help = 'Seed database with sample transfer agent data'
    
    def __init__(self):
        super().__init__()
        self.fake = Faker()
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing data before seeding',
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting database...')
            Transfer.objects.all().delete()
            Certificate.objects.all().delete()
            Holding.objects.all().delete()
            Shareholder.objects.all().delete()
            SecurityClass.objects.all().delete()
            Issuer.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Database reset complete'))
        
        self.stdout.write('Seeding database with sample data...')
        
        issuers = self.create_issuers()
        security_classes = self.create_security_classes(issuers)
        shareholders = self.create_shareholders()
        holdings = self.create_holdings(issuers, security_classes, shareholders)
        certificates = self.create_certificates(issuers, security_classes, shareholders)
        transfers = self.create_transfers(issuers, security_classes, shareholders)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded database!'))
        self.stdout.write(f'  - {len(issuers)} Issuers')
        self.stdout.write(f'  - {len(security_classes)} Security Classes')
        self.stdout.write(f'  - {len(shareholders)} Shareholders')
        self.stdout.write(f'  - {len(holdings)} Holdings')
        self.stdout.write(f'  - {len(certificates)} Certificates')
        self.stdout.write(f'  - {len(transfers)} Transfers')
    
    def create_issuers(self):
        self.stdout.write('Creating issuers...')
        issuers = []
        
        issuer_data = [
            {
                'company_name': 'Green Energy Corporation',
                'ticker_symbol': 'GREN',
                'otc_tier': 'OTCID',
                'cusip': '395234109',
            },
            {
                'company_name': 'TechStart Innovations Inc',
                'ticker_symbol': 'TCHT',
                'otc_tier': 'OTCQB',
                'cusip': '881234567',
            },
            {
                'company_name': 'Private Ventures LLC',
                'ticker_symbol': '',
                'otc_tier': 'NONE',
                'cusip': '',
            }
        ]
        
        states = ['DE', 'NV', 'WY', 'CA', 'NY']
        
        for data in issuer_data:
            issuer, created = Issuer.objects.get_or_create(
                company_name=data['company_name'],
                defaults={
                    'ticker_symbol': data['ticker_symbol'],
                    'cusip': data['cusip'],
                    'cik': str(random.randint(1000000, 9999999)),
                    'incorporation_state': random.choice(states),
                    'incorporation_country': 'US',
                    'incorporation_date': self.fake.date_between(start_date='-10y', end_date='-1y'),
                    'total_authorized_shares': Decimal(random.choice([10000000, 50000000, 100000000])),
                    'par_value': Decimal('0.0001'),
                    'agreement_start_date': self.fake.date_between(start_date='-2y', end_date='today'),
                    'annual_fee': Decimal(random.choice([5000, 7500, 10000, 15000])),
                    'tavs_enabled': random.choice([True, False]),
                    'otc_tier': data['otc_tier'],
                    'primary_contact_name': self.fake.name(),
                    'primary_contact_email': self.fake.company_email(),
                    'primary_contact_phone': self.fake.phone_number()[:20],
                    'is_active': True
                }
            )
            issuers.append(issuer)
        
        return issuers
    
    def create_security_classes(self, issuers):
        self.stdout.write('Creating security classes...')
        security_classes = []
        
        for issuer in issuers:
            common = SecurityClass.objects.create(
                issuer=issuer,
                security_type='COMMON',
                class_designation='Common Stock',
                shares_authorized=issuer.total_authorized_shares,
                par_value=issuer.par_value,
                voting_rights=True,
                votes_per_share=Decimal('1.0'),
                dividend_rights=True,
                is_active=True
            )
            security_classes.append(common)
            
            if random.random() > 0.5:
                preferred = SecurityClass.objects.create(
                    issuer=issuer,
                    security_type='PREFERRED',
                    class_designation='Series A Preferred',
                    shares_authorized=Decimal('5000000'),
                    par_value=issuer.par_value,
                    voting_rights=False,
                    dividend_rights=True,
                    dividend_preference=Decimal('8.0'),
                    liquidation_preference=Decimal('1.5'),
                    conversion_rights=True,
                    converts_to=common,
                    conversion_ratio=Decimal('1.0'),
                    is_active=True
                )
                security_classes.append(preferred)
        
        return security_classes
    
    def create_shareholders(self):
        self.stdout.write('Creating shareholders...')
        shareholders = []
        
        for i in range(35):
            email = f"individual{i:03d}@example.com"
            first_name = f"FirstName{i}"
            last_name = f"LastName{i}"
            
            shareholder, created = Shareholder.objects.get_or_create(
                email=email,
                defaults={
                    'account_type': 'INDIVIDUAL',
                    'first_name': first_name,
                    'last_name': last_name,
                    'address_line1': self.fake.street_address(),
                    'city': self.fake.city(),
                    'state': self.fake.state_abbr(),
                    'zip_code': self.fake.postcode(),
                    'country': 'US',
                    'phone': self.fake.phone_number()[:20],
                    'tax_id_type': 'NONE',
                    'accredited_investor': random.choice([True, False]),
                    'accredited_date': self.fake.date_between(start_date='-1y') if random.random() > 0.5 else None,
                    'kyc_verified': random.choice([True, False]),
                    'is_active': True
                }
            )
            shareholders.append(shareholder)
        
        for i in range(10):
            email = f"entity{i:03d}@example.com"
            company_name = f"Entity Corporation {i}"
            
            shareholder, created = Shareholder.objects.get_or_create(
                email=email,
                defaults={
                    'account_type': 'ENTITY',
                    'entity_name': company_name,
                    'entity_type': random.choice(['Corporation', 'LLC', 'Trust', 'Partnership']),
                    'address_line1': self.fake.street_address(),
                    'city': self.fake.city(),
                    'state': self.fake.state_abbr(),
                    'zip_code': self.fake.postcode(),
                    'country': 'US',
                    'phone': self.fake.phone_number()[:20],
                    'tax_id_type': 'NONE',
                    'accredited_investor': True,
                    'kyc_verified': True,
                    'is_active': True
                }
            )
            shareholders.append(shareholder)
        
        for i in range(5):
            email = f"joint{i:03d}@example.com"
            first_name = f"Joint{i}FirstName"
            last_name = f"Joint{i}LastName"
            
            shareholder, created = Shareholder.objects.get_or_create(
                email=email,
                defaults={
                    'account_type': 'JOINT_TENANTS',
                    'first_name': first_name,
                    'last_name': last_name,
                    'address_line1': self.fake.street_address(),
                    'city': self.fake.city(),
                    'state': self.fake.state_abbr(),
                    'zip_code': self.fake.postcode(),
                    'country': 'US',
                    'phone': self.fake.phone_number()[:20],
                    'tax_id_type': 'NONE',
                    'is_active': True
                }
            )
            shareholders.append(shareholder)
        
        return shareholders
    
    def create_holdings(self, issuers, security_classes, shareholders):
        self.stdout.write('Creating holdings...')
        holdings = []
        
        for i in range(100):
            security_class = random.choice(security_classes)
            shareholder = random.choice(shareholders)
            
            share_quantity = Decimal(random.randint(100, 100000))
            
            holding = Holding.objects.create(
                shareholder=shareholder,
                issuer=security_class.issuer,
                security_class=security_class,
                share_quantity=share_quantity,
                acquisition_date=self.fake.date_between(start_date='-3y', end_date='today'),
                acquisition_price=Decimal(str(round(random.uniform(0.01, 10.0), 4))),
                holding_type=random.choice(['DRS', 'CERTIFICATE']),
                is_restricted=random.choice([True, False]),
                restriction_type=random.choice(['NONE', 'RULE_144', 'REG_D']) if random.random() > 0.7 else ''
            )
            holdings.append(holding)
        
        return holdings
    
    def create_certificates(self, issuers, security_classes, shareholders):
        self.stdout.write('Creating certificates...')
        certificates = []
        
        for issuer in issuers:
            issuer_sec_classes = [sc for sc in security_classes if sc.issuer == issuer]
            
            for i in range(random.randint(5, 10)):
                security_class = random.choice(issuer_sec_classes)
                shareholder = random.choice(shareholders)
                
                cert = Certificate.objects.create(
                    issuer=issuer,
                    security_class=security_class,
                    shareholder=shareholder,
                    certificate_number=f"{issuer.ticker_symbol or 'CERT'}-{i+1:04d}",
                    shares=Decimal(random.randint(100, 10000)),
                    status=random.choice(['OUTSTANDING', 'OUTSTANDING', 'OUTSTANDING', 'CANCELLED']),
                    issue_date=self.fake.date_between(start_date='-3y', end_date='today'),
                    has_legend=random.choice([True, False])
                )
                certificates.append(cert)
        
        return certificates
    
    def create_transfers(self, issuers, security_classes, shareholders):
        self.stdout.write('Creating transfers...')
        transfers = []
        
        for i in range(10):
            security_class = random.choice(security_classes)
            from_shareholder = random.choice(shareholders)
            to_shareholder = random.choice([s for s in shareholders if s != from_shareholder])
            
            transfer = Transfer.objects.create(
                issuer=security_class.issuer,
                security_class=security_class,
                from_shareholder=from_shareholder,
                to_shareholder=to_shareholder,
                share_quantity=Decimal(random.randint(10, 1000)),
                transfer_price=Decimal(str(round(random.uniform(0.01, 5.0), 4))) if random.random() > 0.3 else None,
                transfer_date=self.fake.date_between(start_date='-1y', end_date='today'),
                transfer_type=random.choice(['SALE', 'GIFT', 'INHERITANCE']),
                status=random.choice(['PENDING', 'APPROVED', 'EXECUTED', 'EXECUTED']),
                signature_guaranteed=random.choice([True, False])
            )
            transfers.append(transfer)
        
        return transfers
