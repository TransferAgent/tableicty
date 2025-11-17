# 🔐 AWS SECRETS MANAGER - Configuration Template

This document provides the exact secrets you need to create in AWS Secrets Manager.

**⚠️ CRITICAL:** Use the keys from `/tmp/aws_secrets_SECURE.txt` - NOT the Replit keys

---

## SECRET 1: Database Connection

**Secret Name:** `tableicty/staging/database-url`

**Secret Type:** Other type of secret

**Key/Value:**
```
DATABASE_URL=postgresql://tableicty_admin:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/tableicty_staging
```

**Example:**
```
DATABASE_URL=postgresql://tableicty_admin:MySecurePass123!@tableicty-staging-db.abc123.us-east-1.rds.amazonaws.com:5432/tableicty_staging
```

**Where to get values:**
- `tableicty_admin` - Username you set when creating RDS
- `YOUR_RDS_PASSWORD` - Password you set when creating RDS
- `YOUR_RDS_ENDPOINT` - From RDS Console → Your DB → Connectivity & Security → Endpoint

---

## SECRET 2: Django Secret Key

**Secret Name:** `tableicty/staging/django-secret-key`

**Secret Type:** Other type of secret

**Key/Value:**
```
SECRET_KEY=<Copy STAGING SECRET_KEY from /tmp/aws_secrets_SECURE.txt>
```

**Example:**
```
SECRET_KEY=ojMtdw_fk2m5fL1c6ihlPsj0YlKzWzGjGVBHiSjkEo0OZYyTVkWWCBwk-pIL9hEBb8Q
```

---

## SECRET 3: PGCrypto Encryption Key

**Secret Name:** `tableicty/staging/pgcrypto-key`

**Secret Type:** Other type of secret

**Key/Value:**
```
PGCRYPTO_KEY=<Copy STAGING PGCRYPTO_KEY from /tmp/aws_secrets_SECURE.txt>
```

**Example:**
```
PGCRYPTO_KEY=hvJEOak6o0FiGBUUJBX1bmE8Se7XGmL7p9fQNLwDfYo
```

**⚠️ CRITICAL:** This key encrypts tax IDs (SSN/EIN). NEVER reuse Replit key.

---

## SECRET 4: AWS S3 Credentials

**Secret Name:** `tableicty/staging/aws-s3-credentials`

**Secret Type:** Other type of secret

**Key/Value pairs:**
```json
{
  "AWS_ACCESS_KEY_ID": "<From IAM user creation>",
  "AWS_SECRET_ACCESS_KEY": "<From IAM user creation>",
  "AWS_STORAGE_BUCKET_NAME": "otcsimplified-documents-staging"
}
```

**Where to get values:**
- IAM → Users → tableicty-s3-user → Security Credentials → Access Keys

---

## SECRET 5: Complete Environment Variables (For App Runner)

**Secret Name:** `tableicty/staging/environment`

**Secret Type:** Other type of secret

**Value (JSON format):**
```json
{
  "DATABASE_URL": "postgresql://tableicty_admin:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/tableicty_staging",
  "SECRET_KEY": "<STAGING SECRET_KEY from /tmp/aws_secrets_SECURE.txt>",
  "PGCRYPTO_KEY": "<STAGING PGCRYPTO_KEY from /tmp/aws_secrets_SECURE.txt>",
  "AWS_ACCESS_KEY_ID": "<IAM S3 access key>",
  "AWS_SECRET_ACCESS_KEY": "<IAM S3 secret key>",
  "AWS_STORAGE_BUCKET_NAME": "otcsimplified-documents-staging",
  "AWS_S3_REGION_NAME": "us-east-1",
  "DEBUG": "False",
  "IS_PRODUCTION": "False",
  "USE_S3": "True",
  "ALLOWED_HOSTS": "staging.otcsimplified.com,.awsapprunner.com",
  "CORS_ALLOWED_ORIGINS": "https://staging.otcsimplified.com"
}
```

**This is the PRIMARY secret that App Runner will use.**

---

## PRODUCTION SECRETS (When Ready)

For production deployment, create separate secrets with production keys:

**Secret Names:**
- `tableicty/production/database-url`
- `tableicty/production/django-secret-key`
- `tableicty/production/pgcrypto-key`
- `tableicty/production/aws-s3-credentials`
- `tableicty/production/environment`

**⚠️ CRITICAL DIFFERENCES:**
1. Use **PRODUCTION** keys from `/tmp/aws_secrets_SECURE.txt`
2. Different RDS database: `tableicty_production`
3. Different S3 bucket: `otcsimplified-documents-production`
4. Set `IS_PRODUCTION=True`
5. Domain: `app.otcsimplified.com` or `www.otcsimplified.com`

---

## HOW TO CREATE SECRETS IN AWS

### Method 1: AWS Console (Easiest)

1. Go to **AWS Console** → **Secrets Manager**
2. Click **Store a new secret**
3. Select **Other type of secret**
4. For JSON secrets, click **Plaintext** and paste JSON
5. For key/value, use **Key/value** tab
6. Click **Next**
7. Enter secret name (e.g., `tableicty/staging/environment`)
8. Click **Next** → **Next** → **Store**

### Method 2: AWS CLI

```bash
# Store DATABASE_URL
aws secretsmanager create-secret \
    --name tableicty/staging/database-url \
    --secret-string "postgresql://tableicty_admin:PASSWORD@ENDPOINT:5432/tableicty_staging"

# Store complete environment (from JSON file)
aws secretsmanager create-secret \
    --name tableicty/staging/environment \
    --secret-string file://staging-env.json
```

---

## VERIFICATION CHECKLIST

After creating all secrets:

- [ ] `tableicty/staging/database-url` created
- [ ] `tableicty/staging/django-secret-key` created
- [ ] `tableicty/staging/pgcrypto-key` created
- [ ] `tableicty/staging/aws-s3-credentials` created
- [ ] `tableicty/staging/environment` created (PRIMARY)
- [ ] All keys copied from `/tmp/aws_secrets_SECURE.txt`
- [ ] NO Replit keys used in AWS
- [ ] Staging and production use DIFFERENT keys
- [ ] Deleted `/tmp/aws_secrets_SECURE.txt` after copying

---

## SECURITY BEST PRACTICES

### ✅ DO:
- Use AWS Secrets Manager for ALL sensitive data
- Use different keys for staging vs production
- Enable automatic rotation (quarterly recommended)
- Restrict IAM access to secrets
- Monitor secret access in CloudTrail
- Use strong, randomly generated keys

### ❌ DON'T:
- Never commit secrets to GitHub
- Never reuse exposed keys (Replit key is in docs!)
- Never use same keys across environments
- Never hardcode secrets in application code
- Never share secrets in chat/documents
- Never use weak or predictable keys

---

## IAM PERMISSIONS FOR APP RUNNER

App Runner needs permission to read secrets. Create this IAM policy:

**Policy Name:** `tableicty-secrets-read-policy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:tableicty/staging/*"
      ]
    }
  ]
}
```

Attach this policy to the App Runner service role.

---

## SECRET ROTATION SCHEDULE

**Recommended Rotation:**
- **Quarterly** (every 3 months) for production
- **Annually** for staging
- **Immediately** if compromised

**How to Rotate:**
1. Generate new keys (same method as initial generation)
2. Update secret in Secrets Manager
3. Deploy new App Runner version
4. Verify application works
5. Delete old keys

---

## TROUBLESHOOTING

### App Runner Can't Access Secrets

**Issue:** Permission denied errors

**Solution:**
1. Verify IAM role attached to App Runner service
2. Check IAM policy allows `secretsmanager:GetSecretValue`
3. Ensure secret name exactly matches in App Runner config
4. Check AWS region matches (us-east-1)

### Wrong Key Used

**Issue:** Decryption fails or security error

**Solution:**
1. Verify you're using STAGING keys (not production or Replit)
2. Check `/tmp/aws_secrets_SECURE.txt` for correct values
3. Re-create secret with correct key
4. Redeploy App Runner service

### Secret Not Found

**Issue:** Secret doesn't exist error

**Solution:**
1. Check secret name spelling (case-sensitive)
2. Verify secret exists in correct AWS region
3. Ensure App Runner has permission to access
4. Check secret ARN in CloudWatch logs

---

**Template Version:** 1.0  
**Last Updated:** November 17, 2025  
**Platform:** tableicty Transfer Agent SaaS

**Remember:** Delete `/tmp/aws_secrets_SECURE.txt` after copying all keys to AWS Secrets Manager!
