# Production Deployment Steps

**Date:** December 14, 2025  
**User Email:** info@inlandvalleyautomall.com

## Pre-Deployment Checklist

- [x] All 86 tests passing (40 backend + 46 frontend)
- [x] Seed endpoint implemented and tested locally
- [x] Certificate requests list endpoint added
- [x] Logout graceful (always returns 200)
- [x] Both workflows running correctly locally

## Step 1: Push Code to GitHub

From your local machine or Replit shell:

```bash
git add .
git commit -m "Add seed endpoint, certificate requests list, logout fix"
git push origin main
```

This will trigger AWS App Runner to automatically rebuild and deploy.

## Step 2: Create Shareholder Record on Production

After the deployment completes (~5-10 minutes), access the Django shell on production.

**Option A: Via AWS App Runner Console**
1. Go to AWS Console → App Runner → tableicty service
2. Click "Logs" tab → "Application logs"
3. Use AWS CloudShell or SSM to run the Django shell

**Option B: Via Direct Database Connection**

Connect to your RDS database and run:

```sql
INSERT INTO core_shareholder (
    id,
    email,
    account_type,
    first_name,
    last_name,
    is_active,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    'info@inlandvalleyautomall.com',
    'INDIVIDUAL',
    'Admin',
    'User',
    true,
    NOW(),
    NOW()
);
```

**Option C: Via Django Management Command (if you have shell access)**

```bash
python manage.py shell
```

Then run:

```python
from apps.core.models import Shareholder
Shareholder.objects.create(
    email='info@inlandvalleyautomall.com',
    account_type='INDIVIDUAL',
    first_name='Admin',
    last_name='User',
    is_active=True
)
print("Shareholder created successfully!")
```

## Step 3: Register on Production Frontend

1. Go to: http://tableicty-frontend.s3-website-us-east-1.amazonaws.com
2. Click "Register" or "Sign Up"
3. Use these credentials:
   - **Email:** info@inlandvalleyautomall.com
   - **Password:** (choose a strong password, save it securely!)
4. Complete registration

## Step 4: Seed Test Data

After successful registration and login, call the seed endpoint:

**Using curl:**

```bash
# First, get your access token by logging in
curl -X POST https://2c34uemnqg.us-east-1.awsapprunner.com/api/v1/shareholder/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "info@inlandvalleyautomall.com", "password": "YOUR_PASSWORD"}'

# Copy the "access" token from the response, then call seed:
curl -X POST https://2c34uemnqg.us-east-1.awsapprunner.com/api/v1/shareholder/admin/seed-user-data/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

**Using Browser DevTools:**

1. Log in to the frontend
2. Open Developer Tools (F12) → Console
3. Run:

```javascript
fetch('/api/v1/shareholder/admin/seed-user-data/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + sessionStorage.getItem('access_token'),
    'Content-Type': 'application/json'
  }
}).then(r => r.json()).then(console.log);
```

**Expected Response:**

```json
{
  "message": "Test data seeded successfully",
  "data_created": {
    "holdings": 3,
    "transfers": 6-12,
    "tax_documents": 2
  },
  "shareholder_email": "info@inlandvalleyautomall.com"
}
```

## Step 5: Verify Data

After seeding, refresh the dashboard and verify:
- [ ] Portfolio shows holdings with different companies
- [ ] Transactions page shows transfer history
- [ ] Tax Documents page shows 1099-DIV documents

## Step 6: Remove Seed Endpoint (CRITICAL)

**Tell the Replit Agent to remove the seed endpoint for security.**

The agent will remove:
1. `seed_user_data_view` function from `apps/shareholder/views.py`
2. URL route from `apps/shareholder/urls.py`

Then push another deployment.

## Production URLs

| Service | URL |
|---------|-----|
| Backend API | https://2c34uemnqg.us-east-1.awsapprunner.com |
| Frontend | http://tableicty-frontend.s3-website-us-east-1.amazonaws.com |
| API Docs | https://2c34uemnqg.us-east-1.awsapprunner.com/api/v1/docs/ |
| Health Check | https://2c34uemnqg.us-east-1.awsapprunner.com/api/v1/shareholder/health/ |

## Troubleshooting

**Registration fails with "Shareholder not found":**
- The Shareholder record wasn't created in Step 2
- Verify the email matches exactly (case-sensitive)

**Seed returns "User already has data":**
- Data was already seeded - this is fine!
- Check the dashboard to see your existing data

**403 Forbidden on seed endpoint:**
- Token expired - log in again to get a fresh token
- Make sure you're using the access token, not the refresh token

**App Runner deployment failed:**
- Check App Runner logs for build errors
- Ensure requirements.txt is valid
