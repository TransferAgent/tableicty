# tableicty - Transfer Agent SaaS Platform

## Overview

**tableicty** is a modern Transfer Agent platform designed for OTC/micro-cap companies to manage shareholder registries, stock transfers, and cap tables with full TAVS (Transfer Agent Verified Shares) compliance readiness.

### Company
OTC Simplified Inc.

### Domain
otcsimplified.com

### Target Market
- OTCQX, OTCQB, and OTC Pink companies
- Micro-cap and small-cap public companies
- Companies transitioning to public markets
- Blockchain-ready security token issuers (future)

### Strategic Focus
Modern, cloud-based transfer agent services with blockchain-ready architecture for the next generation of capital markets.

## Current Implementation Status

### ✅ Completed Features (Step 1 - MVP)

1. **Core Database Models** - All 7 models implemented:
   - **Issuer**: Client companies with OTC tier tracking, TAVS status, and blockchain readiness
   - **SecurityClass**: Stock types (Common, Preferred, Warrants, etc.) with conversion rights
   - **Shareholder**: Beneficial owners with encrypted PII (tax IDs), KYC/AML status
   - **Holding**: Shareholder positions supporting both certificates and DRS (Direct Registration System)
   - **Certificate**: Physical and book-entry certificates with status tracking
   - **Transfer**: Complete transfer workflow with multi-stage approval process
   - **AuditLog**: Immutable audit trail for SEC compliance

2. **Database Configuration**
   - PostgreSQL 15+ with UUID primary keys
   - Proper indexing for performance
   - PII encryption using pgcrypto extension
   - Full foreign key constraints and CASCADE protections

3. **Django Admin Interface**
   - Complete admin configuration for all models
   - Search and filter capabilities
   - Custom admin actions (approve transfers, mark accredited investors, etc.)
   - Inline editing for related models
   - Readonly fields for audit compliance

4. **REST API (Django REST Framework)**
   - Full CRUD endpoints for all models
   - Advanced filtering and search
   - Pagination (50 items per page, max 100)
   - Custom actions:
     - `GET /api/v1/issuers/{id}/cap-table/` - Generate cap table
     - `GET /api/v1/issuers/{id}/share-summary/` - Authorized vs issued shares
     - `POST /api/v1/transfers/{id}/approve/` - Approve transfer
     - `POST /api/v1/transfers/{id}/reject/` - Reject transfer
     - `POST /api/v1/transfers/{id}/execute/` - Execute approved transfer with atomic transaction
   - Token authentication ready

5. **API Documentation**
   - Auto-generated OpenAPI/Swagger docs at `/api/docs/`
   - ReDoc documentation at `/api/redoc/`
   - API schema endpoint at `/api/schema/`

6. **Security Features**
   - PII encryption for tax IDs using django-pgcrypto-fields
   - Brute force protection with django-axes (5 failed login limit)
   - Password validation (12+ characters, complexity requirements)
   - CORS configuration for frontend integration
   - Two-factor authentication framework ready (django-otp)

7. **Sample Data Generator**
   - Management command: `python manage.py seed_data`
   - Creates realistic test data:
     - 3 Issuers (Green Energy Corp, TechStart Inc, Private Ventures LLC)
     - 5 Security Classes across issuers
     - 50 Shareholders (30 individuals, 15 entities, 5 joint accounts)
     - 100 Holdings with random distribution
     - 20 Certificates (mix of outstanding/cancelled)
     - 10 Transfers (various statuses)

8. **Development Server**
   - Running on port 5000 (Replit webview compatible)
   - Live reload enabled
   - Proper logging configuration

## Project Structure

```
tableicty/
├── manage.py                          # Django management script
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── pytest.ini                         # Pytest configuration
│
├── config/                            # Django settings
│   ├── __init__.py
│   ├── settings.py                    # Main settings file
│   ├── urls.py                        # URL routing
│   ├── wsgi.py                        # WSGI entry point
│   └── asgi.py                        # ASGI entry point
│
├── apps/
│   ├── core/                          # Core models & business logic
│   │   ├── models.py                  # All 7 database models
│   │   ├── admin.py                   # Django Admin configuration
│   │   ├── apps.py                    # App configuration
│   │   ├── signals.py                 # Audit logging signals (placeholder)
│   │   └── migrations/                # Database migrations
│   │
│   ├── api/                           # REST API layer
│   │   ├── serializers.py             # DRF serializers
│   │   ├── views.py                   # API viewsets
│   │   ├── urls.py                    # API routing
│   │   └── apps.py                    # App configuration
│   │
│   └── reports/                       # Reports & analytics
│       ├── management/
│       │   └── commands/
│       │       └── seed_data.py       # Sample data generator
│       └── apps.py                    # App configuration
│
├── static/                            # Static files (CSS/JS)
└── media/                             # Uploaded files (future)
```

## Technology Stack

### Backend
- **Python 3.11** - Modern, type-hinted Python
- **Django 4.2 LTS** - Stable, long-term support framework
- **Django REST Framework 3.14** - Powerful API framework
- **PostgreSQL 15+** - Production-ready database with pgcrypto for encryption

### Security & Compliance
- **django-pgcrypto-fields** - Field-level encryption for PII
- **django-otp** - Two-factor authentication framework
- **django-axes** - Brute force protection
- **django-environ** - Secure environment variable management

### API & Documentation
- **drf-spectacular** - OpenAPI 3.0 schema generation
- **django-filter** - Advanced filtering for API endpoints
- **django-cors-headers** - CORS support for frontend integration

### Development Tools
- **pytest** - Modern testing framework
- **Faker** - Realistic sample data generation
- **black, flake8, isort** - Code quality tools

### Future (Not in Step 1)
- **Celery + Redis** - Async task processing
- **AWS RDS, S3** - Production infrastructure
- **React** - Admin dashboard UI

## API Endpoints

### Health Check
```
GET /api/v1/health/
```
Returns API status and version information.

### Issuers
```
GET    /api/v1/issuers/                    # List all issuers (paginated)
POST   /api/v1/issuers/                    # Create new issuer
GET    /api/v1/issuers/{id}/               # Get single issuer
PUT    /api/v1/issuers/{id}/               # Update issuer
PATCH  /api/v1/issuers/{id}/               # Partial update
DELETE /api/v1/issuers/{id}/               # Soft delete (set is_active=False)
GET    /api/v1/issuers/{id}/cap-table/     # Generate cap table
GET    /api/v1/issuers/{id}/share-summary/ # Authorized vs issued shares
```

### Security Classes
```
GET    /api/v1/security-classes/           # List all security classes
POST   /api/v1/security-classes/           # Create new class
GET    /api/v1/security-classes/{id}/      # Get single class
PUT    /api/v1/security-classes/{id}/      # Update class
DELETE /api/v1/security-classes/{id}/      # Soft delete
```

### Shareholders
```
GET    /api/v1/shareholders/               # List all shareholders
POST   /api/v1/shareholders/               # Create new shareholder
GET    /api/v1/shareholders/{id}/          # Get single shareholder
PUT    /api/v1/shareholders/{id}/          # Update shareholder
DELETE /api/v1/shareholders/{id}/          # Soft delete
GET    /api/v1/shareholders/{id}/holdings/ # Get all holdings for shareholder
```

### Holdings
```
GET    /api/v1/holdings/                   # List all holdings
POST   /api/v1/holdings/                   # Create new holding
GET    /api/v1/holdings/{id}/              # Get single holding
PUT    /api/v1/holdings/{id}/              # Update holding
DELETE /api/v1/holdings/{id}/              # Soft delete
```

### Certificates
```
GET    /api/v1/certificates/               # List all certificates
POST   /api/v1/certificates/               # Issue new certificate
GET    /api/v1/certificates/{id}/          # Get single certificate
PUT    /api/v1/certificates/{id}/          # Update certificate
```

### Transfers
```
GET    /api/v1/transfers/                  # List all transfers
POST   /api/v1/transfers/                  # Create new transfer request
GET    /api/v1/transfers/{id}/             # Get single transfer
PUT    /api/v1/transfers/{id}/             # Update transfer
POST   /api/v1/transfers/{id}/approve/     # Approve pending transfer
POST   /api/v1/transfers/{id}/reject/      # Reject pending transfer
POST   /api/v1/transfers/{id}/execute/     # Execute approved transfer
```

### Audit Logs
```
GET    /api/v1/audit-logs/                 # Query audit logs
GET    /api/v1/audit-logs/{id}/            # Get single log entry
```

## Database Models

### Issuer (Client Company)
- Company identity (name, ticker, CUSIP, CIK)
- Incorporation details (state, country, date)
- Stock authorization (authorized shares, par value)
- Transfer agent agreement (dates, fees)
- OTC Markets tier classification
- TAVS participation status
- Blockchain readiness flags
- Primary contact information

### SecurityClass (Types of Stock)
- Security type (Common, Preferred, Warrants, etc.)
- Class designation
- Share authorization and par value
- Voting rights and dividend preferences
- Conversion rights and ratios
- Restriction types (Rule 144, Reg D, etc.)
- Legend text for restricted securities

### Shareholder (Beneficial Owner)
- Account type (Individual, Entity, Joint, IRA, etc.)
- Personal/Entity information
- Contact details (address, email, phone)
- **Encrypted** tax ID (SSN/EIN) using pgcrypto
- Accredited investor status
- KYC verification status
- Blockchain wallet address (future)
- Communication preferences

### Holding (Shareholder Position)
- Links shareholder → issuer → security class
- Share quantity (supports fractional shares)
- Acquisition details (date, price, cost basis)
- Holding type (DRS or Physical Certificate)
- Certificate numbers (if applicable)
- Restriction status and removal dates

### Certificate (Physical/Book-Entry)
- Certificate number (unique per issuer)
- Share quantity
- Status (Outstanding, Cancelled, Lost, Replaced)
- Issue and cancellation dates
- Restrictive legend text
- Replacement tracking

### Transfer (Stock Transfer)
- Parties (issuer, security class, from/to shareholders)
- Share quantity and transfer price
- Transfer date and type (Sale, Gift, Inheritance, etc.)
- Workflow status (Pending → Approved → Executed)
- Medallion signature guarantee tracking
- Certificate surrender/issuance
- Blockchain transaction hash (future)
- Processing user and timestamps

### AuditLog (Immutable History)
- User and email (denormalized)
- Action type (Create, Update, Delete, Transfer Executed, etc.)
- Model and object details
- Old and new values (JSON)
- Changed fields array
- Timestamp, IP address, user agent
- Request ID for correlation
- **Append-only**: Cannot be updated or deleted

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ database (provided by Replit)
- Environment variables configured

### Installation
1. Dependencies are already installed via `requirements.txt`
2. Database is already configured and migrated
3. Superuser created: username `admin`, password `admin123`

### Running Locally
The server runs automatically on port 5000 via the configured workflow.

Access points:
- Django Admin: http://localhost:5000/admin/
- API Root: http://localhost:5000/api/v1/
- Swagger Docs: http://localhost:5000/api/docs/
- ReDoc: http://localhost:5000/api/redoc/

### Management Commands
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed sample data
python manage.py seed_data

# Run development server
python manage.py runserver 0.0.0.0:5000
```

## Security Considerations

### Data Protection
- Tax IDs encrypted at rest using PostgreSQL pgcrypto
- Passwords hashed with Django's PBKDF2 algorithm
- Session cookies secured (HTTPS only in production)
- CSRF protection enabled

### Authentication
- Token-based API authentication
- Session-based admin authentication
- Brute force protection (5 failed attempts = 30min lockout)
- Two-factor authentication framework ready

### Compliance
- Immutable audit logging for SEC requirements
- Soft deletes (is_active flag) - no data loss
- Complete change history in AuditLog
- User attribution for all changes

## Next Steps (Future Phases)

### Step 2: Shareholder Portal
- Self-service shareholder interface
- View holdings and transaction history
- Request transfers
- Download tax documents
- Update contact information

### Step 3: Admin Dashboard UI
- React-based professional admin console
- Data visualization and charts
- Advanced filtering and bulk operations
- Document management

### Step 4: Billing & Subscriptions
- Stripe integration
- Tiered pricing models
- Per-issuer, per-shareholder, per-transaction billing

### Step 5: AWS Production Deployment
- RDS PostgreSQL
- ElastiCache Redis
- ECS/Fargate for Django
- S3 for document storage
- CloudFront CDN

### Step 6: TAVS Integration
- Real-time share count reporting to OTC Markets
- Automated daily submissions
- TAVS compliance dashboard

### Step 7: Advanced Features
- Corporate actions (splits, dividends, mergers)
- Automated email notifications
- Advanced reporting and analytics
- Blockchain/tokenization support

## Contact & Support

For questions or support, contact the development team through OTC Simplified Inc.

---

**Last Updated**: November 17, 2025  
**Version**: 1.0.0 (Step 1 MVP)  
**Status**: Development - Core features complete, ready for testing
