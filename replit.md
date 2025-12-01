# tableicty - Transfer Agent SaaS Platform

## Overview

tableicty is a modern Transfer Agent platform designed for OTC/micro-cap companies to manage shareholder registries, stock transfers, and cap tables with full TAVS (Transfer Agent Verified Shares) compliance readiness. The platform aims to provide cloud-based transfer agent services with a blockchain-ready architecture, targeting OTCQX, OTCQB, and OTC Pink companies, as well as micro-cap and small-cap public companies.

## User Preferences

I prefer detailed explanations.
I want iterative development.
Ask before making major changes.
I like clean, readable code with good documentation.
Do not make changes to the `AWS_DEPLOYMENT_GUIDE.md` file.
Do not make changes to the `AWS_SECRETS_TEMPLATE.md` file.
Do not make changes to the `AWS_DEPLOYMENT_READY.md` file.

## System Architecture

The system is built on a Python 3.11/Django 4.2 LTS backend with Django REST Framework for API services. It uses PostgreSQL 15+ with `pgcrypto` for robust data storage and PII encryption.

**Core Features Implemented (MVP):**
- **Database Models:** Seven core models (Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer, AuditLog) handle all essential transfer agent functionalities, including PII encryption and immutable audit trails.
- **Admin Interface:** Full Django Admin configuration for all models with search, filter, and custom actions.
- **REST API:** Comprehensive CRUD endpoints for all models, including custom actions for cap table generation, share summaries, and transfer approvals/execution. API documentation is auto-generated using OpenAPI/Swagger.
- **Security:** Features include PII encryption, brute force protection (`django-axes`), strong password validation, CORS, two-factor authentication framework (`django-otp`), hardened AuditLog immutability with threadlocal flag system, and **production-ready httpOnly cookie authentication** with comprehensive XSS/CSRF protection.
- **httpOnly Cookie Security (✅ COMPLETE):** Refresh tokens stored in httpOnly cookies (NOT accessible to JavaScript), SameSite='Strict' for CSRF protection, secure flag in production (HTTPS only), proper cookie deletion on logout with matching path/domain/samesite attributes to prevent session fixation attacks.
- **Sample Data:** A management command (`seed_data`) creates realistic test data for development and testing.
- **Backend Testing (✅ PRODUCTION READY):** 40/40 tests passing (40 passed, 1 skipped), 76% coverage. Comprehensive test coverage for authentication with httpOnly cookies (including security attribute validation and proper cookie deletion), API endpoints, shareholder data isolation (permissions), AuditLog immutability, and negative-path scenarios.

**Project Structure:**
The project is organized into `config/` for Django settings, `apps/` containing `core/` (models, admin, business logic), `api/` (serializers, views, URLs), and `reports/` (sample data generator).

**Step 2: Shareholder Portal (COMPLETED - 100%):**
- **React Frontend (✅ 100%):** Vite + TypeScript + Tailwind CSS v4 + React Router setup complete
- **Authentication (✅ 100%):** JWT-based auth with httpOnly cookies, login/register, automatic token refresh, protected routes, sessionStorage for access tokens (not localStorage for enhanced security)
- **Dashboard Layout (✅ 100%):** Navigation, routing, user menu, responsive layout
- **Portfolio Dashboard (✅ 100%):** Holdings display with summary cards, detailed table, and Recharts visualizations (pie + bar charts)
- **Transaction History (✅ 100%):** Filterable table (type/status/year), pagination (50/page), detail modals, CSV export with toasts
- **Tax Documents (✅ 100%):** Document list with filters (year/type), status tracking, download functionality with toasts
- **Certificate Conversion (✅ 100%):** Request form with validation, requests table with status tracking, submission toasts
- **Profile Page (✅ 100%):** Display shareholder information with masked tax ID
- **Type System (✅ 100%):** All TypeScript interfaces aligned with backend serializers
- **UX Polish (✅ 100%):** Toast notifications (react-hot-toast) system-wide, skeleton loading states, enhanced empty states with icons
- **Testing Infrastructure (✅ 100%):** Vitest + React Testing Library + @vitest/coverage-v8, comprehensive test suite with 46 tests passing
- **Unit Tests (✅ 11 tests):** API client methods (login, register, logout, holdings, transactions, tax documents, certificates, profile)
- **Component Tests (✅ 9 tests):** SkeletonTable (6 tests), ErrorBoundary (3 tests)
- **Integration Tests (✅ 26 tests):** LoginPage (6), DashboardPage (10), TransactionsPage (10) - covering user workflows, form validation, auth flows, data display, filtering, pagination, modals, CSV export
- **Mock Data (✅ Complete):** All mock fixtures (Holding, Transfer, TaxDocument, CertificateRequest, PortfolioSummary, Shareholder) aligned with production TypeScript interfaces
- **Test Quality (✅ Architect Approved):** Tests exercise primary user workflows, validate formatting, API parameters, and UI behavior - 100% pass rate

**Future Enhancements (Planned):**
- **Admin Dashboard UI:** React-based professional admin console with data visualization.
- **Billing & Subscriptions:** Integration with Stripe for tiered pricing.
- **TAVS Integration:** Real-time share count reporting and compliance.
- **Advanced Features:** Corporate actions, automated notifications, blockchain support.

## External Dependencies

**Backend & Database:**
- **Python 3.11**
- **Django 4.2 LTS**
- **Django REST Framework 3.14**
- **PostgreSQL 15+**

**Security & Compliance:**
- `django-pgcrypto-fields`: Field-level encryption for PII.
- `django-otp`: Two-factor authentication framework.
- `django-axes`: Brute force protection.
- `django-environ`: Secure environment variable management.

**API & Documentation:**
- `drf-spectacular`: OpenAPI 3.0 schema generation.
- `django-filter`: Advanced filtering for API endpoints.
- `django-cors-headers`: CORS support.

**Development Tools:**
- `pytest`: Testing framework.
- `Faker`: Realistic sample data generation.
- `black`, `flake8`, `isort`: Code quality tools.

**AWS Deployment (✅ READY):**
- AWS App Runner (backend) - apprunner.yaml configured
- AWS RDS PostgreSQL 17.6 - provisioned at tableicty-production-db
- AWS ElastiCache Redis 7.1 - provisioned for caching/sessions
- AWS S3 + CloudFront - for frontend static hosting
- AWS Parameter Store - secrets management (KMS encrypted)
- AWS Route 53 - DNS for tableicty.com
- AWS ACM - SSL certificate ready
- `boto3`, `django-storages` (for AWS integration)

**Deployment Documentation:**
- `AWS_APPRUNNER_SETUP.md` - Step-by-step App Runner configuration
- `DEPLOYMENT_CHECKLIST.md` - Complete deployment checklist (780 lines)
- `apprunner.yaml` - App Runner build/run configuration