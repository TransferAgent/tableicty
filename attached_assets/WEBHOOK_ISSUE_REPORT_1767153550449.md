# STRIPE WEBHOOK NOT PROCESSING - DIAGNOSTIC REPORT
**Date:** December 30, 2025  
**Issue:** Webhook events not reaching backend after Stripe Checkout  
**Impact:** Subscriptions not created in database despite successful payment  

---

## PROBLEM SUMMARY

### What Works ✅
- Stripe Checkout opens successfully
- Test card payments complete
- Stripe Customer created: `cus_ThfZp5wiYSQ9`
- Customer ID saved to `core_tenant.stripe_customer_id`
- FRONTEND_URL configured: `https://tableicty.com`
- Stripe Price IDs populated in database

### What Fails ❌
- Webhook events NOT processed by backend
- NO subscription records created in `core_subscription` table
- Dashboard shows "No active subscription"
- App Runner logs show NO incoming webhook requests

---

## STRIPE CONFIGURATION

### Webhook Endpoint (CONFIRMED in Stripe Dashboard)
- **URL:** `https://2c34uemnqg.us-east-1.awsapprunner.com/api/v1/webhooks/stripe/`
- **Name:** "Tableicty Production Webhook"
- **Mode:** TEST
- **Events Listening:**
  - `checkout.session.completed` ✅
  - `customer.subscription.created` ✅
  - `customer.subscription.updated` ✅
  - `customer.subscription.deleted` ✅
  - `invoice.payment_succeeded` ✅

### Stripe Keys (TEST Mode)
- **Location:** AWS Parameter Store
  - `/tableicty/production/STRIPE_SECRET_KEY` (TEST key)
  - `/tableicty/production/STRIPE_PUBLISHABLE_KEY` (TEST key)
  - `/tableicty/production/STRIPE_WEBHOOK_SECRET`

---

## DATABASE STATE

### Test Corp v2 (Test Tenant)
```sql
Tenant ID: 7d6b00e3-2232-4ef6-9b1c-e9d608413224
Name: Test Corp v2
Stripe Customer ID: cus_ThfZp5wiYSQ9 ✅ (TEST customer created)
Subscription: NONE ❌ (no record in core_subscription)
```

### Database Schema Verified
- ✅ `stripe_price_id_monthly` column exists
- ✅ `stripe_price_id_yearly` column exists
- ✅ All 3 tiers have Price IDs populated:
  - STARTER: `price_1SjZ9CFo1fF7b5cOfnOGNNQg`
  - PROFESSIONAL: `price_1SjZDRFo1fF7b5cOn78pXA7W`
  - ENTERPRISE: `price_1SjZFNFo1fF7b5cOcLwd4ZJA`

---

## TESTING PERFORMED

### Test 1: Checkout Flow ✅
1. Logged in as Test Corp v2
2. Went to billing page
3. Clicked "Select Plan" for Professional tier
4. Stripe Checkout opened
5. Entered test card: 4242 4242 4242 4242
6. Completed 2FA with code: 000000
7. Payment succeeded
8. Redirected back to dashboard

### Test 2: Customer Creation ✅
- Query: `SELECT stripe_customer_id FROM core_tenant WHERE name = 'Test Corp v2'`
- Result: `cus_ThfZp5wiYSQ9` ✅

### Test 3: Subscription Creation ❌
- Query: `SELECT * FROM core_subscription WHERE tenant_id = '7d6b00e3-2232-4ef6-9b1c-e9d608413224'`
- Result: **NO ROWS** ❌

### Test 4: App Runner Logs ❌
- Checked logs during checkout attempt
- NO webhook requests logged
- NO POST to `/api/v1/webhooks/stripe/`
- Conclusion: Webhooks not reaching backend

---

## ROOT CAUSE ANALYSIS

### Why Webhooks Are Failing

**Hypothesis 1: Webhook Endpoint Not Responding**
- Stripe sends webhook → Backend returns 404/500/timeout
- Evidence needed: Check Stripe Dashboard webhook attempt logs

**Hypothesis 2: Webhook Secret Mismatch**
- Backend rejects webhook due to invalid signature
- Evidence needed: Check App Runner logs for signature validation errors

**Hypothesis 3: Network/CORS Blocking**
- App Runner security group blocking Stripe IPs
- CORS policy rejecting webhook requests
- Evidence needed: Network trace or security group audit

**Hypothesis 4: Backend Code Not Processing Events**
- Endpoint exists but doesn't update database
- Silent failures in webhook handler
- Evidence needed: Check webhook handler code

---

## REQUIRED FIXES

### Fix 1: Verify Webhook Endpoint Is Reachable
**Action for App Builder:**
```python
# Test if webhook endpoint responds
# In Django shell or create test view:
from django.urls import reverse
print(reverse('stripe-webhook'))  # Should print /api/v1/webhooks/stripe/

# Test endpoint manually:
curl -X POST https://2c34uemnqg.us-east-1.awsapprunner.com/api/v1/webhooks/stripe/ \
  -H "Content-Type: application/json" \
  -d '{"type": "ping"}'
```

**Expected:** Endpoint should respond (even if with error due to missing signature)

---

### Fix 2: Send Test Webhook from Stripe Dashboard
**Action for User:**
1. Go to: https://dashboard.stripe.com/test/webhooks
2. Click webhook endpoint
3. Click "Send test webhook"
4. Select: `checkout.session.completed`
5. Click "Send"
6. Check response status

**Expected:** Should see HTTP response code (200/400/500)

---

### Fix 3: Add Webhook Logging
**Action for App Builder:**
```python
# In apps/core/webhooks.py (or wherever webhook handler is)
import logging
logger = logging.getLogger(__name__)

@csrf_exempt
def stripe_webhook_view(request):
    logger.info(f"Webhook received: {request.body[:200]}")
    
    # Verify signature
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    logger.info(f"Signature header: {sig_header}")
    
    try:
        event = stripe.Webhook.construct_event(
            request.body, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Event type: {event['type']}")
        
        # Process event...
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return HttpResponse(status=400)
```

---

### Fix 4: Manual Subscription Creation (Temporary Workaround)
**If webhook cannot be fixed immediately, manually create subscription:**

```sql
-- Get Test Corp v2's tenant ID and plan ID
SELECT t.id as tenant_id, sp.id as plan_id
FROM core_tenant t, core_subscriptionplan sp
WHERE t.name = 'Test Corp v2' AND sp.tier = 'PROFESSIONAL';

-- Insert subscription record manually
INSERT INTO core_subscription (
    id,
    tenant_id,
    plan_id,
    status,
    stripe_subscription_id,
    current_period_start,
    current_period_end,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    '7d6b00e3-2232-4ef6-9b1c-e9d608413224',  -- Test Corp v2
    (SELECT id FROM core_subscriptionplan WHERE tier = 'PROFESSIONAL'),
    'active',
    'sub_test_manual_' || floor(random() * 1000000),
    NOW(),
    NOW() + INTERVAL '1 month',
    NOW(),
    NOW()
);
```

**WARNING:** This is a workaround. Real Stripe subscription still exists and will try to bill. Webhook MUST be fixed.

---

## NEXT STEPS

### Immediate (App Builder)
1. Check if webhook endpoint URL is registered in Django urls.py
2. Verify webhook handler function exists
3. Add detailed logging to webhook handler
4. Deploy changes
5. Test with Stripe "Send test webhook" feature

### Short Term (1-2 hours)
1. Debug why webhooks aren't reaching backend
2. Fix webhook processing
3. Test end-to-end checkout → subscription creation
4. Verify dashboard shows correct tier

### Long Term (This Week)
1. Add webhook retry logic
2. Add webhook event logging table
3. Create admin dashboard to view webhook history
4. Add alerting for failed webhooks

---

## TEST ACCOUNTS

### Test Corp v2 (Clean Test Tenant)
- **Admin Email:** (Need credentials)
- **Stripe Customer:** `cus_ThfZp5wiYSQ9` (TEST mode)
- **Current Status:** Customer created, NO subscription

### Test John (Also Clean)
- **Admin Email:** whereislycos@yahoo.com
- **Password:** Whereisdad@1
- **Stripe Customer:** NULL (ready for testing)
- **Current Status:** Clean slate

---

## FILES TO CHECK

### Backend Code
- `apps/core/webhooks.py` or `apps/core/views/webhooks.py`
- `apps/core/services/billing.py`
- `config/urls.py` (webhook URL routing)
- `apps/core/tenant_views.py` (line 558 - checkout view)

### Configuration
- AWS Parameter Store: `/tableicty/production/*`
- App Runner environment variables
- Django settings: `STRIPE_WEBHOOK_SECRET`

---

## CONCLUSION

**Checkout flow works perfectly up to the point where Stripe tries to notify our backend.**

**The webhook is the ONLY remaining blocker to full functionality.**

**Priority:** HIGH - Blocking revenue  
**Estimated Fix Time:** 1-2 hours with proper debugging access  

---

**Report Generated:** December 30, 2025  
**Next Update:** After App Builder investigates webhook endpoint
