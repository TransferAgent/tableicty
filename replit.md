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

**AWS Deployment (✅ LIVE - December 7, 2025):**
- AWS App Runner (backend) - **RUNNING** at https://2c34uemnqg.us-east-1.awsapprunner.com
- AWS RDS PostgreSQL 17.6 - Connected (tableicty-production-db)
- AWS S3 Static Hosting - **LIVE** at http://tableicty-frontend.s3-website-us-east-1.amazonaws.com
- AWS Parameter Store - Secrets management (KMS encrypted)
- AWS ElastiCache Redis 7.1 - Provisioned for caching/sessions (optional)
- AWS Route 53 - DNS for tableicty.com (pending custom domain)
- AWS ACM - SSL certificate ready
- `boto3`, `django-storages` (for AWS integration)

**Production Status:**
- ✅ Backend API running with health checks passing (200 OK every 10 seconds)
- ✅ Frontend deployed to S3 with correct API URL configured
- ✅ CORS configured for S3 origin
- ✅ User registration and login working end-to-end
- ✅ Database seeded with test accounts (individual000-004@example.com)
- ✅ Seed endpoint removed for security (December 7, 2025)

**Deployment Fixes Applied:**
- Split `requirements.txt` (production) and `requirements-dev.txt` (development)
- Fixed `IS_PRODUCTION` boolean parsing with `env.bool()`
- Added `HealthCheckMiddleware` to short-circuit health checks (bypass SSL redirect)
- Simplified seed endpoint without faker dependency (removed after use)
- Fixed frontend API URL typo (uemnqq → uemnqg)

**Deployment Documentation:**
- `AWS_APPRUNNER_SETUP.md` - Step-by-step App Runner configuration
- `DEPLOYMENT_CHECKLIST.md` - Complete deployment checklist (780 lines)
- `apprunner.yaml` - App Runner build/run configuration

## Chapter 2: Multi-Tenant SaaS Transformation (In Progress)

**Phase 1: Data Model Foundation (✅ COMPLETE - December 15, 2025)**
- Created 5 new multi-tenant models: Tenant, TenantMembership, SubscriptionPlan, Subscription, TenantInvitation
- Added tenant ForeignKey to all 6 existing models (Issuer, Shareholder, Holding, Certificate, Transfer, AuditLog)
- Created 3 subscription tiers: Starter ($49/mo), Growth ($199/mo), Enterprise ($499/mo)
- Implemented 4-role RBAC: PLATFORM_ADMIN, TENANT_ADMIN, TENANT_STAFF, SHAREHOLDER
- Management command `setup_default_tenant` for backfilling existing data
- All 40 backend tests passing, 74% coverage
- Architect reviewed and approved

**Phase 2: Auth & Isolation (✅ COMPLETE - December 15, 2025)**
- MFA endpoints in `apps/shareholder/mfa.py` - TOTP setup, verification, disable (requires password + TOTP code)
- Custom JWT with tenant claims in `apps/shareholder/jwt.py` - tenant_id, role, mfa_verified claims
- TenantMiddleware in `apps/core/middleware.py` - Uses DB lookups (not JWT claims) for security
- 9 role-based permission classes in `apps/core/permissions.py` for RBAC hierarchy
- TenantQuerySetMixin in `apps/core/mixins.py` for automatic queryset filtering
- 34 tenant isolation tests in `apps/shareholder/tests/test_tenant_isolation.py`
- All 74 backend tests passing, 76% coverage
- Architect reviewed and security fixes applied

**Phase 3: Tenant-Aware APIs (✅ COMPLETE - December 22, 2025)**
- All 7 admin API viewsets updated with TenantQuerySetMixin and TenantScopedPermission for automatic tenant isolation
- Tenant self-registration API in `apps/core/tenant_views.py` - creates tenant, admin user, 14-day trial subscription
- Tenant settings management - GET/PUT for tenant details (admin only)
- Member management API - list, remove members with role-based access
- Invitation system - create/validate/accept invitations with role restrictions
- Current tenant endpoint - returns tenant context or available tenants for multi-tenant users
- Fixed SimpleLazyObject serialization in current_user_view and current_tenant_view
- Updated serializers to match model fields (trial_end, primary_email, etc.)
- 18 new tenant API tests in `apps/core/tests/test_tenant_api.py`
- All 92 backend tests passing, 76% coverage
- Architect reviewed and approved

**Phase 4: Frontend Updates (✅ COMPLETE - December 22, 2025)**
- MFA setup/verification UI in `client/src/components/mfa/` - QR code display, verification form, disable with password+TOTP
- Tenant onboarding wizard in `client/src/components/tenant/TenantOnboarding.tsx` - 3-step wizard with company info, admin account, plan selection
- Role-based route guards in `client/src/components/auth/RoleBasedRoute.tsx` - AdminRoute, StaffRoute, RoleBasedRoute components
- TenantContext in `client/src/contexts/TenantContext.tsx` - tenant state management, role detection, tenant switching
- Security page at `/dashboard/security` - MFA management UI
- Admin page at `/dashboard/admin` - organization settings, member management
- Updated DashboardLayout with tenant display and admin navigation link
- Subscription plans API endpoint for public access
- All 46 frontend tests passing, all 92+ backend tests passing

**Phase 5: Billing & Stripe (✅ COMPLETE - December 22, 2025)**
- Stripe SDK integration with secure key management (production uses SSM Parameter Store)
- Stripe helper module in `apps/core/stripe.py` for client management
- Billing service in `apps/core/services/billing.py` - Customer creation, Checkout sessions, Portal sessions
- Webhook handler in `apps/core/webhooks.py` - handles checkout.session.completed, subscription lifecycle, payment failures
- Billing API endpoints: GET /billing/, POST /billing/checkout/, POST /billing/portal/, POST /billing/cancel/
- Frontend Billing page at `/dashboard/billing` with subscription status, plan selection, upgrade/downgrade UI
- Admin-only access controls for billing management
- All 92 backend tests passing, 46 frontend tests passing, 76% coverage

**Required Environment Variables for Stripe:**
- `STRIPE_SECRET_KEY` - Stripe secret key (sk_live_... or sk_test_...)
- `STRIPE_PUBLISHABLE_KEY` - Stripe publishable key (pk_live_... or pk_test_...)
- `STRIPE_WEBHOOK_SECRET` - Webhook signing secret (whsec_...)
- `FRONTEND_URL` - Frontend URL for Stripe redirects (default: http://localhost:5000)