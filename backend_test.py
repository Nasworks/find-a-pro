#!/usr/bin/env python3
"""
Dispatchr Backend API Testing - Phase 2 Enhanced Features
Tests all newly added endpoints with fresh provider + customer accounts
"""
import requests
import json
from datetime import datetime, timedelta

# Backend URL from frontend/.env
BASE_URL = "https://next-gen-app-39.preview.emergentagent.com/api"

# Test results tracking
test_results = []
passed = 0
failed = 0

def log_test(name, success, details=""):
    global passed, failed
    test_results.append({"test": name, "passed": success, "details": details})
    if success:
        passed += 1
        print(f"✅ {name}")
    else:
        failed += 1
        print(f"❌ {name}: {details}")

def print_summary():
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY: {passed} passed, {failed} failed out of {passed + failed} tests")
    print(f"{'='*80}\n")
    if failed > 0:
        print("FAILED TESTS:")
        for t in test_results:
            if not t["passed"]:
                print(f"  ❌ {t['test']}: {t['details']}")

# ============ SETUP: Create fresh test users ============
print("\n" + "="*80)
print("PHASE 2 BACKEND TESTING - Enhanced Bids, Quotations, Team, etc.")
print("="*80 + "\n")

print("🔧 Setting up test users...")

# Register fresh provider
provider_email = f"provider_{datetime.now().timestamp()}@test.dispatchr.nz"
provider_payload = {
    "email": provider_email,
    "password": "TestPass123!",
    "name": "Test Provider Services",
    "role": "provider",
    "phone": "021-555-1234",
    "city": "Auckland"
}

try:
    r = requests.post(f"{BASE_URL}/auth/register", json=provider_payload, timeout=10)
    if r.status_code == 200:
        provider_data = r.json()
        provider_token = provider_data["token"]
        provider_id = provider_data["user"]["user_id"]
        print(f"✅ Provider registered: {provider_email}")
    else:
        print(f"❌ Provider registration failed: {r.status_code} {r.text}")
        exit(1)
except Exception as e:
    print(f"❌ Provider registration error: {e}")
    exit(1)

# Register fresh customer
customer_email = f"customer_{datetime.now().timestamp()}@test.dispatchr.nz"
customer_payload = {
    "email": customer_email,
    "password": "TestPass123!",
    "name": "Test Customer",
    "role": "customer",
    "phone": "021-555-5678",
    "city": "Auckland"
}

try:
    r = requests.post(f"{BASE_URL}/auth/register", json=customer_payload, timeout=10)
    if r.status_code == 200:
        customer_data = r.json()
        customer_token = customer_data["token"]
        customer_id = customer_data["user"]["user_id"]
        print(f"✅ Customer registered: {customer_email}")
    else:
        print(f"❌ Customer registration failed: {r.status_code} {r.text}")
        exit(1)
except Exception as e:
    print(f"❌ Customer registration error: {e}")
    exit(1)

provider_headers = {"Authorization": f"Bearer {provider_token}"}
customer_headers = {"Authorization": f"Bearer {customer_token}"}

print(f"\n✅ Test users ready\n")

# ============ 1. ENHANCED BIDS ============
print("="*80)
print("1. TESTING ENHANCED BIDS")
print("="*80 + "\n")

# First, customer creates a job
job_payload = {
    "title": "Kitchen Plumbing Upgrade",
    "description": "Replace kitchen sink, install new mixer tap, and fix leaking pipe under sink",
    "category": "plumbing",
    "location": "Auckland Central",
    "budget_min": 500,
    "budget_max": 1200,
    "urgency": "this_week",
    "mode": "quotes"
}

try:
    r = requests.post(f"{BASE_URL}/jobs", json=job_payload, headers=customer_headers, timeout=10)
    if r.status_code == 200:
        job = r.json()
        job_id = job["job_id"]
        log_test("Customer creates job", True, f"Job ID: {job_id}")
    else:
        log_test("Customer creates job", False, f"{r.status_code} {r.text}")
        job_id = None
except Exception as e:
    log_test("Customer creates job", False, str(e))
    job_id = None

# Provider creates enhanced bid with full payload
if job_id:
    bid_payload = {
        "job_id": job_id,
        "amount": 850.0,
        "message": "I can complete this job with high-quality materials and workmanship. 15 years experience in residential plumbing.",
        "eta_days": 3,
        "start_date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "line_items": [
            {"label": "Kitchen sink installation", "qty": 1, "unit_price": 350.0, "total": 350.0},
            {"label": "Mixer tap supply & install", "qty": 1, "unit_price": 280.0, "total": 280.0},
            {"label": "Pipe repair & materials", "qty": 1, "unit_price": 150.0, "total": 150.0},
            {"label": "Labour (2 hours)", "qty": 2, "unit_price": 35.0, "total": 70.0}
        ],
        "warranty_months": 24,
        "payment_terms": "30% deposit, 70% on completion",
        "terms": "All work guaranteed for 24 months. Materials include premium Methven mixer tap. Work includes cleanup and disposal of old fixtures.",
        "documents": [
            {"name": "Plumbing License.pdf", "size": "245KB", "type": "application/pdf", "url": "https://example.com/docs/license.pdf"},
            {"name": "Insurance Certificate.pdf", "size": "180KB", "type": "application/pdf", "url": "https://example.com/docs/insurance.pdf"}
        ]
    }
    
    try:
        r = requests.post(f"{BASE_URL}/bids", json=bid_payload, headers=provider_headers, timeout=10)
        if r.status_code == 200:
            bid = r.json()
            bid_id = bid["bid_id"]
            # Verify all fields are present
            has_line_items = len(bid.get("line_items", [])) == 4
            has_warranty = bid.get("warranty_months") == 24
            has_payment_terms = bid.get("payment_terms") == "30% deposit, 70% on completion"
            has_terms = len(bid.get("terms", "")) > 0
            has_documents = len(bid.get("documents", [])) == 2
            
            if all([has_line_items, has_warranty, has_payment_terms, has_terms, has_documents]):
                log_test("POST /api/bids with full enhanced payload", True, f"Bid ID: {bid_id}, all fields present")
            else:
                missing = []
                if not has_line_items: missing.append("line_items")
                if not has_warranty: missing.append("warranty_months")
                if not has_payment_terms: missing.append("payment_terms")
                if not has_terms: missing.append("terms")
                if not has_documents: missing.append("documents")
                log_test("POST /api/bids with full enhanced payload", False, f"Missing fields: {missing}")
        else:
            log_test("POST /api/bids with full enhanced payload", False, f"{r.status_code} {r.text}")
            bid_id = None
    except Exception as e:
        log_test("POST /api/bids with full enhanced payload", False, str(e))
        bid_id = None

    # GET /api/jobs/{job_id} - verify bids include enhanced fields
    if bid_id:
        try:
            r = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=customer_headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                bids = data.get("bids", [])
                if len(bids) > 0:
                    bid = bids[0]
                    has_line_items = len(bid.get("line_items", [])) > 0
                    has_documents = len(bid.get("documents", [])) > 0
                    has_terms = len(bid.get("terms", "")) > 0
                    has_warranty = "warranty_months" in bid
                    has_payment = "payment_terms" in bid
                    
                    if all([has_line_items, has_documents, has_terms, has_warranty, has_payment]):
                        log_test("GET /api/jobs/{job_id} - bids include enhanced fields", True)
                    else:
                        log_test("GET /api/jobs/{job_id} - bids include enhanced fields", False, "Some enhanced fields missing from bids")
                else:
                    log_test("GET /api/jobs/{job_id} - bids include enhanced fields", False, "No bids returned")
            else:
                log_test("GET /api/jobs/{job_id} - bids include enhanced fields", False, f"{r.status_code}")
        except Exception as e:
            log_test("GET /api/jobs/{job_id} - bids include enhanced fields", False, str(e))

    # POST /api/bids/{bid_id}/counter - create counter-offer
    if bid_id:
        counter_payload = {
            "job_id": job_id,
            "amount": 780.0,
            "message": "Counter-offer: Can we reduce the scope slightly? I can do the same work for $780 if we use a standard tap instead of premium.",
            "eta_days": 3,
            "line_items": [
                {"label": "Kitchen sink installation", "qty": 1, "unit_price": 350.0, "total": 350.0},
                {"label": "Standard mixer tap supply & install", "qty": 1, "unit_price": 210.0, "total": 210.0},
                {"label": "Pipe repair & materials", "qty": 1, "unit_price": 150.0, "total": 150.0},
                {"label": "Labour (2 hours)", "qty": 2, "unit_price": 35.0, "total": 70.0}
            ],
            "warranty_months": 24,
            "payment_terms": "30% deposit, 70% on completion",
            "terms": "All work guaranteed for 24 months. Standard quality tap. Work includes cleanup.",
            "documents": []
        }
        
        try:
            r = requests.post(f"{BASE_URL}/bids/{bid_id}/counter", json=counter_payload, headers=customer_headers, timeout=10)
            if r.status_code == 200:
                counter_bid = r.json()
                counter_bid_id = counter_bid["bid_id"]
                # Verify it's a new bid with revision+1 and previous_bid_id set
                has_revision = counter_bid.get("revision", 1) == 2
                has_previous = counter_bid.get("previous_bid_id") == bid_id
                
                if has_revision and has_previous:
                    log_test("POST /api/bids/{bid_id}/counter - creates new bid with revision+1", True, f"Counter bid ID: {counter_bid_id}")
                else:
                    log_test("POST /api/bids/{bid_id}/counter - creates new bid with revision+1", False, f"revision={counter_bid.get('revision')}, previous_bid_id={counter_bid.get('previous_bid_id')}")
                
                # Verify old bid is marked as "countered"
                r2 = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=customer_headers, timeout=10)
                if r2.status_code == 200:
                    data = r2.json()
                    bids = data.get("bids", [])
                    old_bid = next((b for b in bids if b["bid_id"] == bid_id), None)
                    if old_bid and old_bid.get("status") == "countered":
                        log_test("POST /api/bids/{bid_id}/counter - old bid marked as 'countered'", True)
                    else:
                        log_test("POST /api/bids/{bid_id}/counter - old bid marked as 'countered'", False, f"Old bid status: {old_bid.get('status') if old_bid else 'not found'}")
            else:
                log_test("POST /api/bids/{bid_id}/counter - creates new bid with revision+1", False, f"{r.status_code} {r.text}")
                counter_bid_id = None
        except Exception as e:
            log_test("POST /api/bids/{bid_id}/counter - creates new bid with revision+1", False, str(e))
            counter_bid_id = None

    # Create another bid for reject/withdraw tests
    if job_id:
        bid_payload2 = {
            "job_id": job_id,
            "amount": 950.0,
            "message": "Premium service with 3-year warranty",
            "eta_days": 5,
            "line_items": [{"label": "Full service", "qty": 1, "unit_price": 950.0, "total": 950.0}],
            "warranty_months": 36,
            "payment_terms": "50% upfront, 50% on completion"
        }
        
        try:
            r = requests.post(f"{BASE_URL}/bids", json=bid_payload2, headers=provider_headers, timeout=10)
            if r.status_code == 200:
                bid2 = r.json()
                bid2_id = bid2["bid_id"]
                
                # POST /api/bids/{bid_id}/reject as job owner
                r2 = requests.post(f"{BASE_URL}/bids/{bid2_id}/reject", headers=customer_headers, timeout=10)
                if r2.status_code == 200:
                    # Verify status is rejected
                    r3 = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=customer_headers, timeout=10)
                    if r3.status_code == 200:
                        data = r3.json()
                        bids = data.get("bids", [])
                        rejected_bid = next((b for b in bids if b["bid_id"] == bid2_id), None)
                        if rejected_bid and rejected_bid.get("status") == "rejected":
                            log_test("POST /api/bids/{bid_id}/reject - status='rejected'", True)
                        else:
                            log_test("POST /api/bids/{bid_id}/reject - status='rejected'", False, f"Status: {rejected_bid.get('status') if rejected_bid else 'not found'}")
                else:
                    log_test("POST /api/bids/{bid_id}/reject - status='rejected'", False, f"{r2.status_code}")
            else:
                log_test("POST /api/bids/{bid_id}/reject - status='rejected'", False, "Failed to create second bid")
        except Exception as e:
            log_test("POST /api/bids/{bid_id}/reject - status='rejected'", False, str(e))

    # Create third bid for withdraw test
    if job_id:
        bid_payload3 = {
            "job_id": job_id,
            "amount": 1100.0,
            "message": "High-end materials",
            "eta_days": 7,
            "line_items": [{"label": "Premium service", "qty": 1, "unit_price": 1100.0, "total": 1100.0}],
            "warranty_months": 12,
            "payment_terms": "50% upfront, 50% on completion"
        }
        
        try:
            r = requests.post(f"{BASE_URL}/bids", json=bid_payload3, headers=provider_headers, timeout=10)
            if r.status_code == 200:
                bid3 = r.json()
                bid3_id = bid3["bid_id"]
                
                # POST /api/bids/{bid_id}/withdraw as provider
                r2 = requests.post(f"{BASE_URL}/bids/{bid3_id}/withdraw", headers=provider_headers, timeout=10)
                if r2.status_code == 200:
                    # Verify status is withdrawn
                    r3 = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=customer_headers, timeout=10)
                    if r3.status_code == 200:
                        data = r3.json()
                        bids = data.get("bids", [])
                        withdrawn_bid = next((b for b in bids if b["bid_id"] == bid3_id), None)
                        if withdrawn_bid and withdrawn_bid.get("status") == "withdrawn":
                            log_test("POST /api/bids/{bid_id}/withdraw - status='withdrawn'", True)
                        else:
                            log_test("POST /api/bids/{bid_id}/withdraw - status='withdrawn'", False, f"Status: {withdrawn_bid.get('status') if withdrawn_bid else 'not found'}")
                else:
                    log_test("POST /api/bids/{bid_id}/withdraw - status='withdrawn'", False, f"{r2.status_code}")
            else:
                log_test("POST /api/bids/{bid_id}/withdraw - status='withdrawn'", False, "Failed to create third bid")
        except Exception as e:
            log_test("POST /api/bids/{bid_id}/withdraw - status='withdrawn'", False, str(e))

    # POST /api/bids/{bid_id}/comments - create comment
    if bid_id:
        comment_payload = {"content": "Can you provide more details about the warranty coverage?"}
        try:
            r = requests.post(f"{BASE_URL}/bids/{bid_id}/comments", json=comment_payload, headers=customer_headers, timeout=10)
            if r.status_code == 200:
                comment = r.json()
                if comment.get("content") == comment_payload["content"]:
                    log_test("POST /api/bids/{bid_id}/comments - creates comment", True)
                else:
                    log_test("POST /api/bids/{bid_id}/comments - creates comment", False, "Comment content mismatch")
            else:
                log_test("POST /api/bids/{bid_id}/comments - creates comment", False, f"{r.status_code} {r.text}")
        except Exception as e:
            log_test("POST /api/bids/{bid_id}/comments - creates comment", False, str(e))

    # GET /api/bids/{bid_id}/comments - get comments in chronological order
    if bid_id:
        # Add another comment
        comment_payload2 = {"content": "The warranty covers all parts and labour for 24 months from completion date."}
        try:
            requests.post(f"{BASE_URL}/bids/{bid_id}/comments", json=comment_payload2, headers=provider_headers, timeout=10)
            
            r = requests.get(f"{BASE_URL}/bids/{bid_id}/comments", headers=customer_headers, timeout=10)
            if r.status_code == 200:
                comments = r.json()
                if len(comments) >= 2:
                    # Verify chronological order (first comment should be older)
                    first_time = datetime.fromisoformat(comments[0]["created_at"].replace("Z", "+00:00"))
                    second_time = datetime.fromisoformat(comments[1]["created_at"].replace("Z", "+00:00"))
                    if first_time <= second_time:
                        log_test("GET /api/bids/{bid_id}/comments - returns comments in chronological order", True, f"{len(comments)} comments")
                    else:
                        log_test("GET /api/bids/{bid_id}/comments - returns comments in chronological order", False, "Not in chronological order")
                else:
                    log_test("GET /api/bids/{bid_id}/comments - returns comments in chronological order", False, f"Only {len(comments)} comments found")
            else:
                log_test("GET /api/bids/{bid_id}/comments - returns comments in chronological order", False, f"{r.status_code}")
        except Exception as e:
            log_test("GET /api/bids/{bid_id}/comments - returns comments in chronological order", False, str(e))

# ============ 2. QUOTATIONS ============
print("\n" + "="*80)
print("2. TESTING QUOTATIONS")
print("="*80 + "\n")

# POST /api/quotations with line_items
quote_payload = {
    "client_name": "John Smith",
    "title": "Bathroom Renovation Quote",
    "description": "Full bathroom renovation including tiling, plumbing fixtures, and vanity installation",
    "line_items": [
        {"label": "Bathroom tiles supply & install", "qty": 15, "unit_price": 85.0},
        {"label": "Vanity unit & basin", "qty": 1, "unit_price": 650.0},
        {"label": "Toilet suite", "qty": 1, "unit_price": 420.0},
        {"label": "Shower mixer & rail", "qty": 1, "unit_price": 380.0},
        {"label": "Labour (3 days)", "qty": 3, "unit_price": 450.0}
    ],
    "valid_until": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
    "status": "draft"
}

try:
    r = requests.post(f"{BASE_URL}/quotations", json=quote_payload, headers=provider_headers, timeout=10)
    if r.status_code == 200:
        quote = r.json()
        quote_id = quote["quote_id"]
        
        # Verify auto-computed values
        expected_subtotal = (15 * 85.0) + 650.0 + 420.0 + 380.0 + (3 * 450.0)  # 3975.0
        expected_tax = round(expected_subtotal * 0.15, 2)  # 596.25
        expected_total = round(expected_subtotal + expected_tax, 2)  # 4571.25
        
        actual_subtotal = quote.get("subtotal")
        actual_tax = quote.get("tax")
        actual_total = quote.get("total")
        
        if actual_subtotal == expected_subtotal and actual_tax == expected_tax and actual_total == expected_total:
            log_test("POST /api/quotations - auto-computes subtotal, tax (15%), total", True, f"Subtotal: ${actual_subtotal}, Tax: ${actual_tax}, Total: ${actual_total}")
        else:
            log_test("POST /api/quotations - auto-computes subtotal, tax (15%), total", False, f"Expected: ${expected_subtotal}/${expected_tax}/${expected_total}, Got: ${actual_subtotal}/${actual_tax}/${actual_total}")
    else:
        log_test("POST /api/quotations - auto-computes subtotal, tax (15%), total", False, f"{r.status_code} {r.text}")
        quote_id = None
except Exception as e:
    log_test("POST /api/quotations - auto-computes subtotal, tax (15%), total", False, str(e))
    quote_id = None

# GET /api/quotations/mine
try:
    r = requests.get(f"{BASE_URL}/quotations/mine", headers=provider_headers, timeout=10)
    if r.status_code == 200:
        quotes = r.json()
        if len(quotes) > 0 and any(q["quote_id"] == quote_id for q in quotes):
            log_test("GET /api/quotations/mine - returns provider's quotations", True, f"{len(quotes)} quotations")
        else:
            log_test("GET /api/quotations/mine - returns provider's quotations", False, "Created quote not found in list")
    else:
        log_test("GET /api/quotations/mine - returns provider's quotations", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/quotations/mine - returns provider's quotations", False, str(e))

# PATCH /api/quotations/{quote_id} - update status to "sent"
if quote_id:
    try:
        r = requests.patch(f"{BASE_URL}/quotations/{quote_id}", json={"status": "sent"}, headers=provider_headers, timeout=10)
        if r.status_code == 200:
            updated_quote = r.json()
            if updated_quote.get("status") == "sent":
                log_test("PATCH /api/quotations/{quote_id} - update status to 'sent'", True)
            else:
                log_test("PATCH /api/quotations/{quote_id} - update status to 'sent'", False, f"Status: {updated_quote.get('status')}")
        else:
            log_test("PATCH /api/quotations/{quote_id} - update status to 'sent'", False, f"{r.status_code}")
    except Exception as e:
        log_test("PATCH /api/quotations/{quote_id} - update status to 'sent'", False, str(e))

# DELETE /api/quotations/{quote_id}
# Create a new quote to delete
delete_quote_payload = {
    "client_name": "Test Delete",
    "title": "Test Quote",
    "line_items": [{"label": "Test", "qty": 1, "unit_price": 100.0}]
}
try:
    r = requests.post(f"{BASE_URL}/quotations", json=delete_quote_payload, headers=provider_headers, timeout=10)
    if r.status_code == 200:
        delete_quote_id = r.json()["quote_id"]
        r2 = requests.delete(f"{BASE_URL}/quotations/{delete_quote_id}", headers=provider_headers, timeout=10)
        if r2.status_code == 200:
            # Verify it's deleted
            r3 = requests.get(f"{BASE_URL}/quotations/mine", headers=provider_headers, timeout=10)
            if r3.status_code == 200:
                quotes = r3.json()
                if not any(q["quote_id"] == delete_quote_id for q in quotes):
                    log_test("DELETE /api/quotations/{quote_id} - deletes quotation", True)
                else:
                    log_test("DELETE /api/quotations/{quote_id} - deletes quotation", False, "Quote still exists after delete")
        else:
            log_test("DELETE /api/quotations/{quote_id} - deletes quotation", False, f"{r2.status_code}")
    else:
        log_test("DELETE /api/quotations/{quote_id} - deletes quotation", False, "Failed to create quote for deletion")
except Exception as e:
    log_test("DELETE /api/quotations/{quote_id} - deletes quotation", False, str(e))

# ============ 3. TEAM MEMBERS ============
print("\n" + "="*80)
print("3. TESTING TEAM MEMBERS")
print("="*80 + "\n")

# POST /api/team
team_payload = {
    "name": "Mike Johnson",
    "role": "Plumber",
    "phone": "021-555-9999",
    "email": "mike@testprovider.nz",
    "hourly_rate": 55.0,
    "skills": ["residential plumbing", "gas fitting", "drainage"]
}

try:
    r = requests.post(f"{BASE_URL}/team", json=team_payload, headers=provider_headers, timeout=10)
    if r.status_code == 200:
        member = r.json()
        member_id = member["member_id"]
        # Verify all fields
        has_name = member.get("name") == "Mike Johnson"
        has_role = member.get("role") == "Plumber"
        has_rate = member.get("hourly_rate") == 55.0
        has_skills = len(member.get("skills", [])) == 3
        
        if all([has_name, has_role, has_rate, has_skills]):
            log_test("POST /api/team - creates team member with all fields", True, f"Member ID: {member_id}")
        else:
            log_test("POST /api/team - creates team member with all fields", False, "Some fields missing or incorrect")
    else:
        log_test("POST /api/team - creates team member with all fields", False, f"{r.status_code} {r.text}")
        member_id = None
except Exception as e:
    log_test("POST /api/team - creates team member with all fields", False, str(e))
    member_id = None

# GET /api/team
try:
    r = requests.get(f"{BASE_URL}/team", headers=provider_headers, timeout=10)
    if r.status_code == 200:
        team = r.json()
        if len(team) > 0 and any(m["member_id"] == member_id for m in team):
            log_test("GET /api/team - returns team members", True, f"{len(team)} members")
        else:
            log_test("GET /api/team - returns team members", False, "Created member not found")
    else:
        log_test("GET /api/team - returns team members", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/team - returns team members", False, str(e))

# PATCH /api/team/{member_id} - update status
if member_id:
    try:
        r = requests.patch(f"{BASE_URL}/team/{member_id}", json={"status": "on_job"}, headers=provider_headers, timeout=10)
        if r.status_code == 200:
            updated_member = r.json()
            if updated_member.get("status") == "on_job":
                log_test("PATCH /api/team/{member_id} - updates status", True)
            else:
                log_test("PATCH /api/team/{member_id} - updates status", False, f"Status: {updated_member.get('status')}")
        else:
            log_test("PATCH /api/team/{member_id} - updates status", False, f"{r.status_code}")
    except Exception as e:
        log_test("PATCH /api/team/{member_id} - updates status", False, str(e))

# DELETE /api/team/{member_id}
# Create another member to delete
delete_member_payload = {"name": "Test Delete", "role": "Worker"}
try:
    r = requests.post(f"{BASE_URL}/team", json=delete_member_payload, headers=provider_headers, timeout=10)
    if r.status_code == 200:
        delete_member_id = r.json()["member_id"]
        r2 = requests.delete(f"{BASE_URL}/team/{delete_member_id}", headers=provider_headers, timeout=10)
        if r2.status_code == 200:
            # Verify deleted
            r3 = requests.get(f"{BASE_URL}/team", headers=provider_headers, timeout=10)
            if r3.status_code == 200:
                team = r3.json()
                if not any(m["member_id"] == delete_member_id for m in team):
                    log_test("DELETE /api/team/{member_id} - deletes member", True)
                else:
                    log_test("DELETE /api/team/{member_id} - deletes member", False, "Member still exists")
        else:
            log_test("DELETE /api/team/{member_id} - deletes member", False, f"{r2.status_code}")
    else:
        log_test("DELETE /api/team/{member_id} - deletes member", False, "Failed to create member for deletion")
except Exception as e:
    log_test("DELETE /api/team/{member_id} - deletes member", False, str(e))

# ============ 4. TRADES BOARD ============
print("\n" + "="*80)
print("4. TESTING TRADES BOARD")
print("="*80 + "\n")

# POST /api/trades-board
trade_job_payload = {
    "title": "Need a sparky for commercial fit-out",
    "description": "Looking for a qualified electrician to help with a commercial office fit-out in Auckland CBD. 3-day job, good rates.",
    "trade": "electrician",
    "budget": 2500.0,
    "urgency": "this_week"
}

try:
    r = requests.post(f"{BASE_URL}/trades-board", json=trade_job_payload, headers=provider_headers, timeout=10)
    if r.status_code == 200:
        trade_job = r.json()
        trade_job_id = trade_job["trade_job_id"]
        log_test("POST /api/trades-board - creates trade job", True, f"Trade job ID: {trade_job_id}")
    else:
        log_test("POST /api/trades-board - creates trade job", False, f"{r.status_code} {r.text}")
except Exception as e:
    log_test("POST /api/trades-board - creates trade job", False, str(e))

# GET /api/trades-board
try:
    r = requests.get(f"{BASE_URL}/trades-board", headers=provider_headers, timeout=10)
    if r.status_code == 200:
        trade_jobs = r.json()
        if len(trade_jobs) > 0:
            log_test("GET /api/trades-board - returns trade jobs", True, f"{len(trade_jobs)} jobs")
        else:
            log_test("GET /api/trades-board - returns trade jobs", False, "No trade jobs found")
    else:
        log_test("GET /api/trades-board - returns trade jobs", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/trades-board - returns trade jobs", False, str(e))

# ============ 5. EXTERNAL JOBS ============
print("\n" + "="*80)
print("5. TESTING EXTERNAL JOBS")
print("="*80 + "\n")

# GET /api/external-jobs - should return >=6 seeded partner leads
try:
    r = requests.get(f"{BASE_URL}/external-jobs", headers=provider_headers, timeout=10)
    if r.status_code == 200:
        external_jobs = r.json()
        if len(external_jobs) >= 6:
            # Verify they have required fields
            sample = external_jobs[0]
            has_source = "source" in sample
            has_title = "title" in sample
            has_category = "category" in sample
            
            if all([has_source, has_title, has_category]):
                log_test("GET /api/external-jobs - returns >=6 seeded partner leads", True, f"{len(external_jobs)} leads")
            else:
                log_test("GET /api/external-jobs - returns >=6 seeded partner leads", False, "Missing required fields")
        else:
            log_test("GET /api/external-jobs - returns >=6 seeded partner leads", False, f"Only {len(external_jobs)} leads found")
    else:
        log_test("GET /api/external-jobs - returns >=6 seeded partner leads", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/external-jobs - returns >=6 seeded partner leads", False, str(e))

# ============ 6. GPS DEVICES ============
print("\n" + "="*80)
print("6. TESTING GPS DEVICES")
print("="*80 + "\n")

# POST /api/gps-devices
gps_payload = {
    "name": "Van #1 GPS Tracker",
    "assigned_to": member_id if member_id else None
}

try:
    r = requests.post(f"{BASE_URL}/gps-devices", json=gps_payload, headers=provider_headers, timeout=10)
    if r.status_code == 200:
        device = r.json()
        device_id = device["device_id"]
        log_test("POST /api/gps-devices - creates GPS device", True, f"Device ID: {device_id}")
    else:
        log_test("POST /api/gps-devices - creates GPS device", False, f"{r.status_code} {r.text}")
except Exception as e:
    log_test("POST /api/gps-devices - creates GPS device", False, str(e))

# GET /api/gps-devices
try:
    r = requests.get(f"{BASE_URL}/gps-devices", headers=provider_headers, timeout=10)
    if r.status_code == 200:
        devices = r.json()
        if len(devices) > 0:
            log_test("GET /api/gps-devices - returns GPS devices", True, f"{len(devices)} devices")
        else:
            log_test("GET /api/gps-devices - returns GPS devices", False, "No devices found")
    else:
        log_test("GET /api/gps-devices - returns GPS devices", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/gps-devices - returns GPS devices", False, str(e))

# ============ 7. MEMBERSHIP ============
print("\n" + "="*80)
print("7. TESTING MEMBERSHIP")
print("="*80 + "\n")

# GET /api/membership/plans - should return 4 plans
try:
    r = requests.get(f"{BASE_URL}/membership/plans", timeout=10)
    if r.status_code == 200:
        plans = r.json()
        if len(plans) == 4:
            # Verify plan IDs
            plan_ids = [p["id"] for p in plans]
            expected_ids = ["free", "starter", "pro", "enterprise"]
            if all(pid in plan_ids for pid in expected_ids):
                log_test("GET /api/membership/plans - returns 4 plans (free, starter, pro, enterprise)", True)
            else:
                log_test("GET /api/membership/plans - returns 4 plans (free, starter, pro, enterprise)", False, f"Plan IDs: {plan_ids}")
        else:
            log_test("GET /api/membership/plans - returns 4 plans (free, starter, pro, enterprise)", False, f"Found {len(plans)} plans")
    else:
        log_test("GET /api/membership/plans - returns 4 plans (free, starter, pro, enterprise)", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/membership/plans - returns 4 plans (free, starter, pro, enterprise)", False, str(e))

# GET /api/membership/mine - returns current plan
try:
    r = requests.get(f"{BASE_URL}/membership/mine", headers=provider_headers, timeout=10)
    if r.status_code == 200:
        membership = r.json()
        if "plan" in membership:
            log_test("GET /api/membership/mine - returns current plan", True, f"Plan: {membership['plan']['id']}")
        else:
            log_test("GET /api/membership/mine - returns current plan", False, "No plan field in response")
    else:
        log_test("GET /api/membership/mine - returns current plan", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/membership/mine - returns current plan", False, str(e))

# POST /api/membership/subscribe - switch to pro plan
try:
    r = requests.post(f"{BASE_URL}/membership/subscribe", json={"plan_id": "pro"}, headers=provider_headers, timeout=10)
    if r.status_code == 200:
        result = r.json()
        if result.get("plan", {}).get("id") == "pro":
            # Verify it persisted
            r2 = requests.get(f"{BASE_URL}/membership/mine", headers=provider_headers, timeout=10)
            if r2.status_code == 200:
                membership = r2.json()
                if membership.get("plan", {}).get("id") == "pro":
                    log_test("POST /api/membership/subscribe - switches plan to 'pro'", True)
                else:
                    log_test("POST /api/membership/subscribe - switches plan to 'pro'", False, "Plan not persisted")
        else:
            log_test("POST /api/membership/subscribe - switches plan to 'pro'", False, f"Plan: {result.get('plan', {}).get('id')}")
    else:
        log_test("POST /api/membership/subscribe - switches plan to 'pro'", False, f"{r.status_code}")
except Exception as e:
    log_test("POST /api/membership/subscribe - switches plan to 'pro'", False, str(e))

# ============ 8. WARRANTY CLAIMS ============
print("\n" + "="*80)
print("8. TESTING WARRANTY CLAIMS")
print("="*80 + "\n")

# POST /api/warranty-claims
claim_payload = {
    "subject": "Leaking tap after installation",
    "description": "The kitchen tap installed 3 months ago has started leaking from the base. Water is pooling under the sink.",
    "provider_name": "Test Provider Services"
}

try:
    r = requests.post(f"{BASE_URL}/warranty-claims", json=claim_payload, headers=customer_headers, timeout=10)
    if r.status_code == 200:
        claim = r.json()
        claim_id = claim["claim_id"]
        log_test("POST /api/warranty-claims - creates warranty claim", True, f"Claim ID: {claim_id}")
    else:
        log_test("POST /api/warranty-claims - creates warranty claim", False, f"{r.status_code} {r.text}")
except Exception as e:
    log_test("POST /api/warranty-claims - creates warranty claim", False, str(e))

# GET /api/warranty-claims/mine
try:
    r = requests.get(f"{BASE_URL}/warranty-claims/mine", headers=customer_headers, timeout=10)
    if r.status_code == 200:
        claims = r.json()
        if len(claims) > 0:
            log_test("GET /api/warranty-claims/mine - returns user's claims", True, f"{len(claims)} claims")
        else:
            log_test("GET /api/warranty-claims/mine - returns user's claims", False, "No claims found")
    else:
        log_test("GET /api/warranty-claims/mine - returns user's claims", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/warranty-claims/mine - returns user's claims", False, str(e))

# ============ 9. REFERRALS ============
print("\n" + "="*80)
print("9. TESTING REFERRALS")
print("="*80 + "\n")

# GET /api/referrals/mine - should return incoming, outgoing, invite_code, reward_per_signup
try:
    r = requests.get(f"{BASE_URL}/referrals/mine", headers=provider_headers, timeout=10)
    if r.status_code == 200:
        referrals = r.json()
        has_incoming = "incoming" in referrals
        has_outgoing = "outgoing" in referrals
        has_code = "invite_code" in referrals
        has_reward = referrals.get("reward_per_signup") == 25
        
        if all([has_incoming, has_outgoing, has_code, has_reward]):
            log_test("GET /api/referrals/mine - returns {incoming, outgoing, invite_code, reward_per_signup:25}", True, f"Invite code: {referrals['invite_code']}")
        else:
            missing = []
            if not has_incoming: missing.append("incoming")
            if not has_outgoing: missing.append("outgoing")
            if not has_code: missing.append("invite_code")
            if not has_reward: missing.append("reward_per_signup")
            log_test("GET /api/referrals/mine - returns {incoming, outgoing, invite_code, reward_per_signup:25}", False, f"Missing: {missing}")
    else:
        log_test("GET /api/referrals/mine - returns {incoming, outgoing, invite_code, reward_per_signup:25}", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/referrals/mine - returns {incoming, outgoing, invite_code, reward_per_signup:25}", False, str(e))

# ============ 10. JOB HISTORY ============
print("\n" + "="*80)
print("10. TESTING JOB HISTORY")
print("="*80 + "\n")

# GET /api/job-history - should return only closed bookings (done, paid, cancelled)
try:
    r = requests.get(f"{BASE_URL}/job-history", headers=customer_headers, timeout=10)
    if r.status_code == 200:
        history = r.json()
        # Verify all bookings have status in ["done", "paid", "cancelled"]
        if len(history) > 0:
            all_closed = all(b.get("status") in ["done", "paid", "cancelled"] for b in history)
            if all_closed:
                log_test("GET /api/job-history - returns closed bookings only", True, f"{len(history)} bookings")
            else:
                log_test("GET /api/job-history - returns closed bookings only", False, "Contains non-closed bookings")
        else:
            # No history is OK for new user
            log_test("GET /api/job-history - returns closed bookings only", True, "0 bookings (new user)")
    else:
        log_test("GET /api/job-history - returns closed bookings only", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/job-history - returns closed bookings only", False, str(e))

# ============ 11. COST GUIDE ============
print("\n" + "="*80)
print("11. TESTING COST GUIDE")
print("="*80 + "\n")

# GET /api/cost-guide - should return >=15 entries
try:
    r = requests.get(f"{BASE_URL}/cost-guide", timeout=10)
    if r.status_code == 200:
        guide = r.json()
        if len(guide) >= 15:
            # Verify structure
            sample = guide[0]
            has_category = "category" in sample
            has_job = "job" in sample
            has_low = "low" in sample
            has_high = "high" in sample
            has_avg = "avg" in sample
            has_unit = "unit" in sample
            
            if all([has_category, has_job, has_low, has_high, has_avg, has_unit]):
                log_test("GET /api/cost-guide - returns >=15 entries with {category, job, low, high, avg, unit}", True, f"{len(guide)} entries")
            else:
                log_test("GET /api/cost-guide - returns >=15 entries with {category, job, low, high, avg, unit}", False, "Missing required fields")
        else:
            log_test("GET /api/cost-guide - returns >=15 entries with {category, job, low, high, avg, unit}", False, f"Only {len(guide)} entries")
    else:
        log_test("GET /api/cost-guide - returns >=15 entries with {category, job, low, high, avg, unit}", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/cost-guide - returns >=15 entries with {category, job, low, high, avg, unit}", False, str(e))

# GET /api/cost-guide?category=Plumbing - test filter
try:
    r = requests.get(f"{BASE_URL}/cost-guide?category=Plumbing", timeout=10)
    if r.status_code == 200:
        guide = r.json()
        if len(guide) > 0:
            # Verify all entries are Plumbing category
            all_plumbing = all(e.get("category") == "Plumbing" for e in guide)
            if all_plumbing:
                log_test("GET /api/cost-guide?category=Plumbing - filters by category", True, f"{len(guide)} plumbing entries")
            else:
                log_test("GET /api/cost-guide?category=Plumbing - filters by category", False, "Contains non-Plumbing entries")
        else:
            log_test("GET /api/cost-guide?category=Plumbing - filters by category", False, "No plumbing entries found")
    else:
        log_test("GET /api/cost-guide?category=Plumbing - filters by category", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/cost-guide?category=Plumbing - filters by category", False, str(e))

# ============ 12. TRADE STORE ============
print("\n" + "="*80)
print("12. TESTING TRADE STORE")
print("="*80 + "\n")

# GET /api/products - verify products include unit field, featured boolean, brand
try:
    r = requests.get(f"{BASE_URL}/products", timeout=10)
    if r.status_code == 200:
        products = r.json()
        if len(products) >= 27:
            # Check sample product for required fields
            sample = products[0]
            has_unit = "unit" in sample
            has_featured = "featured" in sample
            has_brand = "brand" in sample
            
            # Verify categories
            categories = set(p.get("category") for p in products)
            expected_categories = ["Power Tools", "Hand Tools", "Equipment", "Fixings", "Materials", 
                                 "Plumbing", "Electrical", "Kitsets", "Safety & PPE"]
            has_categories = any(cat in categories for cat in expected_categories)
            
            # Check for various unit types
            units = set(p.get("unit") for p in products if "unit" in p)
            expected_units = ["kit", "each", "bag", "kitset", "10pk", "20pk"]
            has_units = any(unit in units for unit in expected_units)
            
            if all([has_unit, has_featured, has_brand, has_categories, has_units]):
                log_test("GET /api/products - includes unit, featured, brand fields; >=27 products across categories", True, f"{len(products)} products, {len(categories)} categories")
            else:
                missing = []
                if not has_unit: missing.append("unit")
                if not has_featured: missing.append("featured")
                if not has_brand: missing.append("brand")
                if not has_categories: missing.append("expected categories")
                if not has_units: missing.append("expected units")
                log_test("GET /api/products - includes unit, featured, brand fields; >=27 products across categories", False, f"Missing: {missing}")
        else:
            log_test("GET /api/products - includes unit, featured, brand fields; >=27 products across categories", False, f"Only {len(products)} products")
    else:
        log_test("GET /api/products - includes unit, featured, brand fields; >=27 products across categories", False, f"{r.status_code}")
except Exception as e:
    log_test("GET /api/products - includes unit, featured, brand fields; >=27 products across categories", False, str(e))

# ============ PRINT SUMMARY ============
print_summary()
