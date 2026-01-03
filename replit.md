# tableicty - Transfer Agent SaaS Platform

## Overview

tableicty is a modern, cloud-based Transfer Agent platform designed for OTC/micro-cap and small-cap public companies. It enables management of shareholder registries, stock transfers, and cap tables with full TAVS compliance readiness. The platform offers core transfer agent functionalities, a shareholder portal, and is evolving into a multi-tenant SaaS with blockchain-ready architecture.

## User Preferences

I prefer detailed explanations.
I want iterative development.
Ask before making major changes.
I like clean, readable code with good documentation.
Do not make changes to the `AWS_DEPLOYMENT_GUIDE.md` file.
Do not make changes to the `AWS_SECRETS_TEMPLATE.md` file.
Do not make changes to the `AWS_DEPLOYMENT_READY.md` file.

## System Architecture

The system is built on a Python 3.11/Django 4.2 LTS backend with Django REST Framework, using PostgreSQL 15+ with `pgcrypto` for data storage and PII encryption. The frontend is a React application built with Vite, TypeScript, and Tailwind CSS.

**Core Features & Design:**
-   **Database Models:** Seven core models manage transfer agent functions (Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer, AuditLog), with PII encryption and immutable audit trails.
-   **Admin Interface & REST API:** Comprehensive Django Admin and RESTful API (CRUD) for all models, including cap table generation, share summaries, and transfer approvals. API documentation is generated via OpenAPI/Swagger.
-   **Security:** Features include PII encryption, brute force protection, strong password validation, CORS, two-factor authentication (TOTP), and robust httpOnly cookie authentication with XSS/CSRF protection. Audit logs are hardened for immutability.
-   **Shareholder Portal (React Frontend):** Provides JWT-based authentication with httpOnly cookies, a dashboard with holdings and visualizations, transaction history, tax document access, certificate conversion requests with PDF download support, and profile management.
-   **Multi-Tenant SaaS Architecture:** Implements a multi-tenant data model with tenant-scoped data isolation, role-based access control (PLATFORM_ADMIN, TENANT_ADMIN, TENANT_STAFF, SHAREHOLDER), tenant self-registration, and subscription management.
-   **Email Service:** Integration with AWS SES for sending shareholder invitations, welcome emails, test emails, share update notifications, and certificate workflow emails. Features smart email detection that sends "Share Update" notifications to existing shareholders with accounts (showing additional shares and new totals) or invitation emails with JWT tokens for new shareholders who need to register. Certificate workflow emails include admin alerts for new requests and shareholder notifications for approvals/rejections.
-   **Certificate Workflow:** Complete certificate conversion system with CertificateRequest model (DRS_TO_CERT, CERT_TO_DRS conversions), status tracking (PENDING/PROCESSING/COMPLETED/REJECTED), PDF certificate generation using ReportLab, email notifications at each stage, and configurable admin notification emails via TenantSettings.
-   **Shareholder Management (Admin Console):** CRUD operations for shareholders, ability to issue shares, and a comprehensive cap table view with breakdowns by security class and top shareholders.
-   **Billing:** Stripe integration for subscription management, checkout sessions, and webhook handling.

**Technical Implementations:**
-   **Backend Testing:** Comprehensive test suite with high coverage for API endpoints, authentication, data isolation, and audit log immutability.
-   **Frontend Testing:** Vitest and React Testing Library for unit, component, and integration tests covering user workflows and UI behavior.
-   **Deployment:** Utilizes AWS App Runner for the backend, AWS RDS for PostgreSQL, AWS S3 for static frontend hosting, AWS Parameter Store for secrets, and AWS SES for email.

## External Dependencies

**Backend & Database:**
-   Python 3.11
-   Django 4.2 LTS
-   Django REST Framework 3.14
-   PostgreSQL 15+

**Frontend:**
-   React
-   Vite
-   TypeScript
-   Tailwind CSS

**Security & Compliance:**
-   `django-pgcrypto-fields` (for PII encryption)
-   `django-otp` (for Two-Factor Authentication)
-   `django-axes` (for brute force protection)

**API & Documentation:**
-   `drf-spectacular` (for OpenAPI 3.0 schema generation)
-   `django-filter` (for API filtering)
-   `django-cors-headers` (for CORS support)

**Cloud Services & Integrations:**
-   AWS App Runner
-   AWS RDS PostgreSQL
-   AWS S3
-   AWS Parameter Store
-   AWS SES (Simple Email Service)
-   Stripe (for billing and subscriptions)

**PDF Generation:**
-   `reportlab` (for stock certificate PDF generation)

**Development Tools:**
-   `pytest`
-   `Faker`
-   `black`, `flake8`, `isort`

## Recent Changes (Sprint 2 - Certificate Workflow)

**Date:** January 2026

**Backend Additions:**
- TenantSettings model with certificate_notification_emails field for admin alert configuration
- CertificateRequest model extensions: certificate_pdf_url, shareholder_email_sent, admin_email_sent tracking fields
- TenantSettings API endpoint (GET/PATCH) at `/api/v1/tenant/certificate-settings/`
- Email triggers: admin alert on certificate request submission, shareholder notifications on approve/reject
- PDF certificate generation service using ReportLab with proper fractional share formatting
- PDF download endpoint at `/api/v1/shareholder/certificate-requests/{uuid}/download/`

**Frontend Additions:**
- Updated CertificatesPage with PDF download button for completed DRS_TO_CERT conversions
- Rejection reason display with expandable rows for rejected certificate requests
- Certificate number display for completed requests
- CertificateSettingsCard component for managing admin notification emails (Settings tab in AdminPage)
- CertificateRequestModal component for viewing, approving, and rejecting certificate requests
- AdminPage "Certificates" tab with request list, status filtering, pending badge count, and refresh capability
- ShareholdersPage certificate status icon indicator (PENDING/PROCESSING/COMPLETED/REJECTED)
- AdminCertificateRequest type and API client methods (getAdminCertificateRequests, approveCertificateRequest, rejectCertificateRequest)

## Sprint 3 - Deal Desk (Planned)

**Start Date:** January 4, 2026
**Duration:** 2 weeks

### Overview
AI-powered term sheet analyzer that helps founders understand dilution, identify red flags, and generate negotiation scenarios. Founders upload a term sheet PDF and receive a comprehensive analysis in ~60 seconds.

### Architecture Decision
**Modular Monolith Approach** - Build Deal Desk as a separate Django app (`apps/deal_desk/`) within Tableicty, with clean API boundaries at `/api/v1/deal-desk/`. This allows future apps to call the API while avoiding premature microservice complexity. Can be extracted to standalone service later if needed.

### Key Technical Decisions
- **OpenAI Integration:** User's own API key (not Replit AI Integrations)
- **Processing:** Async via Celery task queue
- **File Storage:** AWS S3 for term sheet PDFs
- **Subscription Plan Field:** TBD - needs to be added to Tenant model

### Phase 1: Backend Foundation (Days 1-4)
- **1A:** Django models (TermSheetAnalysis, AnalysisRedFlag, AnalysisScenario)
- **1B:** API endpoints (upload, list, detail) with serializers
- **1C:** OpenAI integration + PDF extraction service (pdfplumber + PyPDF2 fallback)

### Phase 2: Frontend (Days 5-10)
- **2A:** Upload page with drag-and-drop
- **2B:** Dashboard listing analyses with status polling
- **2C:** Analysis report with dilution charts, red flags, scenarios

### Phase 3: Integration & Polish (Days 11-14)
- **3A:** Routes and navigation
- **3B:** Error handling and usage limits (Free: 1, Starter: 3/year, Pro: unlimited)
- **3C:** Testing and deployment

### New Dependencies (to be added)
- `openai` (OpenAI Python client)
- `pdfplumber` (PDF text extraction)
- `PyPDF2` (PDF fallback)
- `celery` (async task processing)
- `react-dropzone` (frontend file upload)
- `recharts` (frontend charts)

## Staging/Production Workflow

### Environment URLs
| Environment | Backend | Frontend S3 | CloudFront |
|-------------|---------|-------------|------------|
| **Production** | `https://2c54uemnqg.us-east-1.awsapprunner.com` | `tableicty-frontend` | `https://tableicty.com` |
| **Staging** | `https://ghh6zmq2i6.us-east-1.awsapprunner.com` | `tableicty-staging-frontend` | TBD |

### Git Branch Strategy
- `main` → Production (auto-deploys backend via App Runner)
- `staging` → Staging (auto-deploys backend via App Runner)

### Development Rule
**ALL new features are built in STAGING first, then promoted to production after testing.**

### Frontend Deployment Files
- `client/dist/` → Production build
- `client/dist-staging/` → Staging build
- `client/dist.zip` → Production deployment package
- `client/dist-staging.zip` → Staging deployment package

### Staging Deploy Commands
```bash
# Backend (auto-deploys via App Runner when pushed to staging branch)
git checkout staging
git push origin staging

# Frontend
aws s3 sync client/dist-staging/ s3://tableicty-staging-frontend/ --delete
aws cloudfront create-invalidation --distribution-id [STAGING_ID] --paths "/*"
```

### Production Deploy Commands (after staging approval)
```bash
# Merge staging to main
git checkout main
git merge staging
git push origin main

# Frontend
aws s3 sync client/dist/ s3://tableicty-frontend/ --delete
aws cloudfront create-invalidation --distribution-id [PROD_ID] --paths "/*"
```

### Rollback Plan
If production breaks:
1. Backend: `git revert HEAD && git push origin main` (App Runner auto-deploys)
2. Frontend: Re-deploy previous version from backup or last known good commit