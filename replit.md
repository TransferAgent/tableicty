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