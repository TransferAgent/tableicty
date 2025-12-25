# Staging Environment Setup Guide

**Date**: December 25, 2025  
**Purpose**: Deploy multi-tenancy Phase 1 to staging before production

---

## Overview

This guide creates a complete staging environment to test the multi-tenancy deployment before promoting to production.

| Component | Production | Staging |
|-----------|------------|---------|
| Backend | tableicty-backend | tableicty-staging-backend |
| Database | tableicty-production-db | tableicty-staging-db |
| Frontend | tableicty-frontend S3 | tableicty-staging S3 |
| URL | https://tableicty.com | Staging App Runner URL |

---

## Step 1: Backup Production Database (10 min)

### Create RDS Snapshot

1. Go to **AWS RDS Console** → **Databases**
2. Select `tableicty-production-db`
3. Click **Actions** → **Take snapshot**
4. Snapshot name: `tableicty-production-backup-20251225`
5. Wait for snapshot status: **Available**

---

## Step 2: Create Staging Database (15-20 min)

### Restore Snapshot to New Instance

1. Go to **RDS** → **Snapshots**
2. Select `tableicty-production-backup-20251225`
3. Click **Actions** → **Restore snapshot**
4. Configure:
   - **DB instance identifier**: `tableicty-staging-db`
   - **DB instance class**: `db.t3.micro` (cost-effective for staging)
   - **VPC**: Same as production
   - **Security group**: Same as production (allows App Runner access)
   - **Public accessibility**: No
5. Click **Restore DB instance**
6. Wait for status: **Available** (~10-15 min)

### Record Staging Database Endpoint

```
Endpoint: tableicty-staging-db.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com
Port: 5432
Database: tableicty_production (same as snapshot)
```

---

## Step 3: Configure Staging Parameter Store (10 min)

Create new parameters under `/tableicty/staging/`:

### Required Parameters

Go to **AWS Systems Manager** → **Parameter Store** → **Create parameter**

| Parameter Name | Type | Value |
|---------------|------|-------|
| `/tableicty/staging/DATABASE_URL` | SecureString | `postgresql://tableicty_admin:<password>@tableicty-staging-db.xxxx.us-east-1.rds.amazonaws.com:5432/tableicty_production` |
| `/tableicty/staging/SECRET_KEY` | SecureString | Copy from production |
| `/tableicty/staging/PGCRYPTO_KEY` | SecureString | Copy from production |
| `/tableicty/staging/STRIPE_SECRET_KEY` | SecureString | Use TEST key: `sk_test_...` |
| `/tableicty/staging/STRIPE_PUBLISHABLE_KEY` | String | Use TEST key: `pk_test_...` |
| `/tableicty/staging/STRIPE_WEBHOOK_SECRET` | SecureString | Create new webhook for staging |
| `/tableicty/staging/FRONTEND_URL` | String | Staging App Runner URL (update after Step 4) |

### Copy Values from Production

```bash
# Get production values (run in AWS CloudShell)
aws ssm get-parameter --name "/tableicty/production/SECRET_KEY" --with-decryption --query "Parameter.Value" --output text
aws ssm get-parameter --name "/tableicty/production/PGCRYPTO_KEY" --with-decryption --query "Parameter.Value" --output text
```

---

## Step 4: Create Staging App Runner Service (15-20 min)

### Create New Service

1. Go to **AWS App Runner** → **Create service**

2. **Source and deployment**:
   - Source type: **Source code repository**
   - Provider: GitHub
   - Repository: Same as production
   - Branch: `main`
   - Deployment trigger: Manual

3. **Build settings**:
   - Configuration file: Use `apprunner.yaml` (create in next step)

4. **Service settings**:
   - Service name: `tableicty-staging-backend`
   - CPU: 0.25 vCPU (cost-effective)
   - Memory: 0.5 GB
   - Port: 8000

5. **Networking**:
   - Custom VPC: Yes
   - VPC connector: Same as production (`tableicty-vpc-connector`)

6. **Environment variables** (reference Parameter Store):

| Variable | Value Source |
|----------|-------------|
| `DATABASE_URL` | `arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/staging/DATABASE_URL` |
| `SECRET_KEY` | `arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/staging/SECRET_KEY` |
| `PGCRYPTO_KEY` | `arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/staging/PGCRYPTO_KEY` |
| `STRIPE_SECRET_KEY` | `arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/staging/STRIPE_SECRET_KEY` |
| `STRIPE_PUBLISHABLE_KEY` | `arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/staging/STRIPE_PUBLISHABLE_KEY` |
| `STRIPE_WEBHOOK_SECRET` | `arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/staging/STRIPE_WEBHOOK_SECRET` |
| `IS_PRODUCTION` | `False` (plain text) |
| `DEBUG` | `False` (plain text) |
| `ALLOWED_HOSTS` | `*` (plain text - staging only) |

7. **IAM Role**: Attach `Tableicty-ParameterStore-ReadAccess` policy

8. Click **Create & deploy**

### Record Staging URL

After deployment completes:
```
Staging URL: https://xxxxxxxxxx.us-east-1.awsapprunner.com
```

Update Parameter Store:
```bash
aws ssm put-parameter --name "/tableicty/staging/FRONTEND_URL" --value "https://xxxxxxxxxx.us-east-1.awsapprunner.com" --type String --overwrite
```

---

## Step 5: Run Migrations on Staging (5 min)

### Option A: Via App Runner Logs (Automatic)

Migrations run automatically on startup via the build command.

### Option B: Manual via AWS CloudShell

If you need to run commands manually, connect to the staging database:

```bash
# Install psql in CloudShell
sudo yum install postgresql15 -y

# Connect to staging database
psql "postgresql://tableicty_admin:<password>@tableicty-staging-db.xxxx.us-east-1.rds.amazonaws.com:5432/tableicty_production"

# Verify multi-tenancy tables exist
\dt core_tenant*
\dt core_subscription*
```

---

## Step 6: Run Data Migration Command (5 min)

After the App Runner service is running, trigger the data backfill:

### Option A: Create a One-Time API Endpoint (Recommended)

Add temporary endpoint to run the command, then remove after use.

### Option B: Via Direct Database

Connect to staging database and verify data:

```sql
-- Check if default tenant exists
SELECT * FROM core_tenant;

-- Check subscription plans
SELECT * FROM core_subscriptionplan;

-- Verify existing data has tenant assignments
SELECT COUNT(*) FROM core_issuer WHERE tenant_id IS NOT NULL;
SELECT COUNT(*) FROM core_shareholder WHERE tenant_id IS NOT NULL;
```

---

## Step 7: Staging Validation Checklist (20-30 min)

### Health Check

- [ ] Staging App Runner status: **Running**
- [ ] Health endpoint returns 200: `curl https://staging-url/api/v1/health/`

### Authentication

- [ ] Login with `testadmin@tableicty.com` works
- [ ] JWT tokens issued correctly
- [ ] Token refresh works

### Billing

- [ ] Billing page loads: `/dashboard/billing`
- [ ] Subscription status displays correctly
- [ ] "Unlimited" displays instead of "-1" for Enterprise plan

### Multi-Tenancy (New Features)

- [ ] Tenant registration endpoint works: `POST /api/v1/tenant/register/`
- [ ] Default tenant has been created
- [ ] Existing data backfilled with tenant_id

### Database Verification

```sql
-- Core tenant tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'core_tenant%';

-- Expected: core_tenant, core_tenantmembership, core_tenantinvitation

-- Subscription tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'core_subscription%';

-- Expected: core_subscription, core_subscriptionplan
```

---

## Step 8: Promote to Production

After staging validation passes:

1. **Backup production database** (new snapshot)
2. **Deploy to production App Runner** (trigger deployment)
3. **Run data migration** on production
4. **Verify production** using same checklist
5. **Delete staging resources** (optional, to save costs)

---

## Rollback Plan

If issues occur during staging or production deployment:

### Database Rollback

1. Go to RDS → Snapshots
2. Select the pre-deployment snapshot
3. Restore to replace the affected database

### Code Rollback

1. Go to App Runner → Service → Deployments
2. Select previous successful deployment
3. Click "Redeploy"

---

## Cost Estimates (Staging)

| Resource | Hourly Cost | Daily Cost |
|----------|------------|------------|
| RDS db.t3.micro | ~$0.02 | ~$0.48 |
| App Runner 0.25 vCPU | ~$0.01 | ~$0.24 |
| **Total** | ~$0.03 | ~$0.72 |

**Recommendation**: Delete staging resources after successful production deployment to minimize costs.

---

## Quick Reference Commands

```bash
# AWS CLI - List staging parameters
aws ssm get-parameters-by-path --path "/tableicty/staging" --recursive

# Check App Runner service status
aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='tableicty-staging-backend']"

# View App Runner logs
aws apprunner describe-service --service-arn <arn> --query "Service.Status"
```
