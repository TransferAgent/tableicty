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
-   **Shareholder Portal (React Frontend):** Provides JWT-based authentication with httpOnly cookies, a dashboard with holdings and visualizations, transaction history, tax document access, certificate conversion requests, and profile management.
-   **Multi-Tenant SaaS Architecture:** Implements a multi-tenant data model with tenant-scoped data isolation, role-based access control (PLATFORM_ADMIN, TENANT_ADMIN, TENANT_STAFF, SHAREHOLDER), tenant self-registration, and subscription management.
-   **Email Service:** Integration with AWS SES for sending shareholder invitations, welcome emails, and test emails, utilizing JWT invite tokens for secure registration.
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

**Development Tools:**
-   `pytest`
-   `Faker`
-   `black`, `flake8`, `isort`