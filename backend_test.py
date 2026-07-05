"""
Comprehensive Backend API Tests for Dispatchr
Tests all endpoints according to the review request
"""
import requests
import random
import json
from datetime import datetime, timedelta

# Backend URL from frontend/.env
BASE_URL = "https://next-gen-app-39.preview.emergentagent.com/api"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "total": 0
}

def log_test(name, passed, details=""):
    """Log test result"""
    test_results["total"] += 1
    if passed:
        test_results["passed"].append(name)
        print(f"✅ PASS: {name}")
    else:
        test_results["failed"].append({"name": name, "details": details})
        print(f"❌ FAIL: {name}")
        if details:
            print(f"   Details: {details}")

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {test_results['total']}")
    print(f"Passed: {len(test_results['passed'])}")
    print(f"Failed: {len(test_results['failed'])}")
    print(f"Success Rate: {len(test_results['passed'])/test_results['total']*100:.1f}%")
    
    if test_results['failed']:
        print("\n❌ FAILED TESTS:")
        for fail in test_results['failed']:
            print(f"  - {fail['name']}")
            if fail['details']:
                print(f"    {fail['details']}")
    print("="*80)

# Test data
rand_suffix = random.randint(1000, 9999)
customer_a_email = f"tester_a_{rand_suffix}@dispatchr.demo"
provider_b_email = f"tester_b_{rand_suffix}@dispatchr.demo"
customer_a_token = None
provider_b_token = None
customer_a_id = None
provider_b_id = None

print("="*80)
print("DISPATCHR BACKEND API TESTS")
print("="*80)
print(f"Base URL: {BASE_URL}")
print(f"Customer A: {customer_a_email}")
print(f"Provider B: {provider_b_email}")
print("="*80 + "\n")

# ============================================================================
# 1. AUTH TESTS (HIGH PRIORITY)
# ============================================================================
print("\n🔐 TESTING AUTH ENDPOINTS\n")

# 1.1 Register Customer A
try:
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Test Customer A",
        "email": customer_a_email,
        "password": "demo1234",
        "role": "customer"
    }, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "user" in data and "token" in data:
            customer_a_token = data["token"]
            customer_a_id = data["user"]["user_id"]
            log_test("Auth: Register customer A", True)
        else:
            log_test("Auth: Register customer A", False, "Missing user or token in response")
    else:
        log_test("Auth: Register customer A", False, f"Status {resp.status_code}: {resp.text}")
except Exception as e:
    log_test("Auth: Register customer A", False, str(e))

# 1.2 Duplicate registration should fail with 400
try:
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Test Customer A",
        "email": customer_a_email,
        "password": "demo1234",
        "role": "customer"
    }, timeout=10)
    
    if resp.status_code == 400:
        log_test("Auth: Duplicate register returns 400", True)
    else:
        log_test("Auth: Duplicate register returns 400", False, f"Expected 400, got {resp.status_code}")
except Exception as e:
    log_test("Auth: Duplicate register returns 400", False, str(e))

# 1.3 Login with correct credentials
try:
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": customer_a_email,
        "password": "demo1234"
    }, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "user" in data and "token" in data:
            log_test("Auth: Login with correct credentials", True)
        else:
            log_test("Auth: Login with correct credentials", False, "Missing user or token")
    else:
        log_test("Auth: Login with correct credentials", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Auth: Login with correct credentials", False, str(e))

# 1.4 Login with wrong password should return 401
try:
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": customer_a_email,
        "password": "wrongpassword"
    }, timeout=10)
    
    if resp.status_code == 401:
        log_test("Auth: Wrong password returns 401", True)
    else:
        log_test("Auth: Wrong password returns 401", False, f"Expected 401, got {resp.status_code}")
except Exception as e:
    log_test("Auth: Wrong password returns 401", False, str(e))

# 1.5 GET /auth/me with token
try:
    resp = requests.get(f"{BASE_URL}/auth/me", 
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "user_id" in data and data["user_id"] == customer_a_id:
            log_test("Auth: GET /auth/me returns user", True)
        else:
            log_test("Auth: GET /auth/me returns user", False, "User data mismatch")
    else:
        log_test("Auth: GET /auth/me returns user", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Auth: GET /auth/me returns user", False, str(e))

# 1.6 Register Provider B
try:
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Test Provider B",
        "email": provider_b_email,
        "password": "demo1234",
        "role": "provider"
    }, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "user" in data and "token" in data:
            provider_b_token = data["token"]
            provider_b_id = data["user"]["user_id"]
            log_test("Auth: Register provider B", True)
        else:
            log_test("Auth: Register provider B", False, "Missing user or token")
    else:
        log_test("Auth: Register provider B", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Auth: Register provider B", False, str(e))

# 1.7 Role switching - Customer A switches to provider
try:
    resp = requests.patch(f"{BASE_URL}/auth/role",
                         headers={"Authorization": f"Bearer {customer_a_token}"},
                         json={"role": "provider"},
                         timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("role") == "provider":
            log_test("Auth: Role switch to provider", True)
            # Switch back to customer for remaining tests
            requests.patch(f"{BASE_URL}/auth/role",
                         headers={"Authorization": f"Bearer {customer_a_token}"},
                         json={"role": "customer"},
                         timeout=10)
        else:
            log_test("Auth: Role switch to provider", False, "Role not updated")
    else:
        log_test("Auth: Role switch to provider", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Auth: Role switch to provider", False, str(e))

# ============================================================================
# 2. JOBS & BIDS TESTS (HIGH PRIORITY)
# ============================================================================
print("\n💼 TESTING JOBS & BIDS ENDPOINTS\n")

job_id = None
bid_id = None
booking_id = None

# 2.1 Customer A creates a job
try:
    resp = requests.post(f"{BASE_URL}/jobs",
                        headers={"Authorization": f"Bearer {customer_a_token}"},
                        json={
                            "title": "Fix leaking kitchen tap",
                            "description": "Kitchen tap is dripping constantly, needs urgent repair",
                            "category": "plumbing",
                            "budget_min": 100,
                            "budget_max": 300,
                            "urgency": "asap"
                        },
                        timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "job_id" in data:
            job_id = data["job_id"]
            log_test("Jobs: Create job as customer", True)
        else:
            log_test("Jobs: Create job as customer", False, "No job_id in response")
    else:
        log_test("Jobs: Create job as customer", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Jobs: Create job as customer", False, str(e))

# 2.2 GET /jobs/mine (as Customer A)
try:
    resp = requests.get(f"{BASE_URL}/jobs/mine",
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            found = any(j.get("job_id") == job_id for j in data)
            if found:
                log_test("Jobs: GET /jobs/mine shows created job", True)
            else:
                log_test("Jobs: GET /jobs/mine shows created job", False, "Job not found in list")
        else:
            log_test("Jobs: GET /jobs/mine shows created job", False, "Empty or invalid response")
    else:
        log_test("Jobs: GET /jobs/mine shows created job", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Jobs: GET /jobs/mine shows created job", False, str(e))

# 2.3 GET /jobs/board (as Provider B)
try:
    resp = requests.get(f"{BASE_URL}/jobs/board",
                       headers={"Authorization": f"Bearer {provider_b_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            found = any(j.get("job_id") == job_id for j in data)
            if found:
                log_test("Jobs: GET /jobs/board shows job", True)
            else:
                log_test("Jobs: GET /jobs/board shows job", False, "Job not found on board")
        else:
            log_test("Jobs: GET /jobs/board shows job", False, "Empty or invalid response")
    else:
        log_test("Jobs: GET /jobs/board shows job", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Jobs: GET /jobs/board shows job", False, str(e))

# 2.4 GET /jobs/{job_id}
try:
    resp = requests.get(f"{BASE_URL}/jobs/{job_id}",
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "job" in data and "bids" in data:
            log_test("Jobs: GET /jobs/{job_id} returns job + bids", True)
        else:
            log_test("Jobs: GET /jobs/{job_id} returns job + bids", False, "Missing job or bids")
    else:
        log_test("Jobs: GET /jobs/{job_id} returns job + bids", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Jobs: GET /jobs/{job_id} returns job + bids", False, str(e))

# 2.5 Provider B creates a bid
try:
    resp = requests.post(f"{BASE_URL}/bids",
                        headers={"Authorization": f"Bearer {provider_b_token}"},
                        json={
                            "job_id": job_id,
                            "amount": 200,
                            "message": "I can help with this plumbing issue",
                            "eta_days": 2
                        },
                        timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "bid_id" in data:
            bid_id = data["bid_id"]
            log_test("Bids: Create bid as provider", True)
        else:
            log_test("Bids: Create bid as provider", False, "No bid_id in response")
    else:
        log_test("Bids: Create bid as provider", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Bids: Create bid as provider", False, str(e))

# 2.6 GET /bids/mine (as Provider B)
try:
    resp = requests.get(f"{BASE_URL}/bids/mine",
                       headers={"Authorization": f"Bearer {provider_b_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            found = any(b.get("bid_id") == bid_id for b in data)
            if found:
                log_test("Bids: GET /bids/mine shows bid", True)
            else:
                log_test("Bids: GET /bids/mine shows bid", False, "Bid not found")
        else:
            log_test("Bids: GET /bids/mine shows bid", False, "Empty or invalid response")
    else:
        log_test("Bids: GET /bids/mine shows bid", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Bids: GET /bids/mine shows bid", False, str(e))

# 2.7 Customer A accepts the bid
try:
    resp = requests.post(f"{BASE_URL}/bids/{bid_id}/accept",
                        headers={"Authorization": f"Bearer {customer_a_token}"},
                        timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "booking_id" in data:
            booking_id = data["booking_id"]
            log_test("Bids: Accept bid creates booking", True)
        else:
            log_test("Bids: Accept bid creates booking", False, "No booking_id in response")
    else:
        log_test("Bids: Accept bid creates booking", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Bids: Accept bid creates booking", False, str(e))

# ============================================================================
# 3. BOOKINGS TESTS (HIGH PRIORITY)
# ============================================================================
print("\n📅 TESTING BOOKINGS ENDPOINTS\n")

# 3.1 GET /bookings/mine (as Customer A)
try:
    resp = requests.get(f"{BASE_URL}/bookings/mine",
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            found = any(b.get("booking_id") == booking_id for b in data)
            if found:
                log_test("Bookings: GET /bookings/mine (customer) shows booking", True)
            else:
                log_test("Bookings: GET /bookings/mine (customer) shows booking", False, "Booking not found")
        else:
            log_test("Bookings: GET /bookings/mine (customer) shows booking", False, "Empty response")
    else:
        log_test("Bookings: GET /bookings/mine (customer) shows booking", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Bookings: GET /bookings/mine (customer) shows booking", False, str(e))

# 3.2 GET /bookings/mine (as Provider B)
try:
    resp = requests.get(f"{BASE_URL}/bookings/mine",
                       headers={"Authorization": f"Bearer {provider_b_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            found = any(b.get("booking_id") == booking_id for b in data)
            if found:
                log_test("Bookings: GET /bookings/mine (provider) shows booking", True)
            else:
                log_test("Bookings: GET /bookings/mine (provider) shows booking", False, "Booking not found")
        else:
            log_test("Bookings: GET /bookings/mine (provider) shows booking", False, "Empty response")
    else:
        log_test("Bookings: GET /bookings/mine (provider) shows booking", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Bookings: GET /bookings/mine (provider) shows booking", False, str(e))

# 3.3 Update booking status through pipeline
statuses = ["en_route", "working", "done", "paid"]
for status in statuses:
    try:
        resp = requests.patch(f"{BASE_URL}/bookings/{booking_id}/status",
                            headers={"Authorization": f"Bearer {provider_b_token}"},
                            json={"status": status},
                            timeout=10)
        
        if resp.status_code == 200:
            log_test(f"Bookings: Update status to '{status}'", True)
        else:
            log_test(f"Bookings: Update status to '{status}'", False, f"Status {resp.status_code}")
    except Exception as e:
        log_test(f"Bookings: Update status to '{status}'", False, str(e))

# ============================================================================
# 4. MESSAGES TESTS (MEDIUM PRIORITY)
# ============================================================================
print("\n💬 TESTING MESSAGES ENDPOINTS\n")

thread_id = None

# 4.1 Customer A creates thread with Provider B
try:
    resp = requests.post(f"{BASE_URL}/threads",
                        headers={"Authorization": f"Bearer {customer_a_token}"},
                        json={
                            "other_user_id": provider_b_id,
                            "subject": "Hello Provider",
                            "initial_message": "Hi there, I have a question about the job"
                        },
                        timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "thread_id" in data:
            thread_id = data["thread_id"]
            log_test("Messages: Create thread with initial message", True)
        else:
            log_test("Messages: Create thread with initial message", False, "No thread_id")
    else:
        log_test("Messages: Create thread with initial message", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Messages: Create thread with initial message", False, str(e))

# 4.2 GET /threads (as Customer A)
try:
    resp = requests.get(f"{BASE_URL}/threads",
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            found = any(t.get("thread_id") == thread_id for t in data)
            if found:
                log_test("Messages: GET /threads shows thread", True)
            else:
                log_test("Messages: GET /threads shows thread", False, "Thread not found")
        else:
            log_test("Messages: GET /threads shows thread", False, "Empty response")
    else:
        log_test("Messages: GET /threads shows thread", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Messages: GET /threads shows thread", False, str(e))

# 4.3 GET /threads/{thread_id}/messages
try:
    resp = requests.get(f"{BASE_URL}/threads/{thread_id}/messages",
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "thread" in data and "messages" in data:
            log_test("Messages: GET /threads/{id}/messages returns messages", True)
        else:
            log_test("Messages: GET /threads/{id}/messages returns messages", False, "Missing thread or messages")
    else:
        log_test("Messages: GET /threads/{id}/messages returns messages", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Messages: GET /threads/{id}/messages returns messages", False, str(e))

# 4.4 POST /messages (Provider B replies)
try:
    resp = requests.post(f"{BASE_URL}/messages",
                        headers={"Authorization": f"Bearer {provider_b_token}"},
                        json={
                            "thread_id": thread_id,
                            "content": "How much will it cost?"
                        },
                        timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "message_id" in data:
            log_test("Messages: POST /messages appends message", True)
        else:
            log_test("Messages: POST /messages appends message", False, "No message_id")
    else:
        log_test("Messages: POST /messages appends message", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Messages: POST /messages appends message", False, str(e))

# ============================================================================
# 5. MARKETPLACE TESTS (MEDIUM PRIORITY)
# ============================================================================
print("\n🛒 TESTING MARKETPLACE ENDPOINTS\n")

# 5.1 GET /products (should return 20+ products)
try:
    resp = requests.get(f"{BASE_URL}/products", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) >= 20:
            log_test("Marketplace: GET /products returns 20+ products", True)
        else:
            log_test("Marketplace: GET /products returns 20+ products", False, f"Only {len(data)} products")
    else:
        log_test("Marketplace: GET /products returns 20+ products", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Marketplace: GET /products returns 20+ products", False, str(e))

# 5.2 GET /products?category=Heating%20%26%20Cooling
try:
    resp = requests.get(f"{BASE_URL}/products?category=Heating%20%26%20Cooling", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            # Check if all products are in the correct category
            all_correct = all(p.get("category") == "Heating & Cooling" for p in data)
            if all_correct:
                log_test("Marketplace: GET /products?category filters correctly", True)
            else:
                log_test("Marketplace: GET /products?category filters correctly", False, "Wrong category in results")
        else:
            log_test("Marketplace: GET /products?category filters correctly", False, "Empty response")
    else:
        log_test("Marketplace: GET /products?category filters correctly", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Marketplace: GET /products?category filters correctly", False, str(e))

# 5.3 GET /products?q=heat (search)
try:
    resp = requests.get(f"{BASE_URL}/products?q=heat", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            log_test("Marketplace: GET /products?q=heat returns matching", True)
        else:
            log_test("Marketplace: GET /products?q=heat returns matching", False, "No results")
    else:
        log_test("Marketplace: GET /products?q=heat returns matching", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Marketplace: GET /products?q=heat returns matching", False, str(e))

# 5.4 GET /products/p001
try:
    resp = requests.get(f"{BASE_URL}/products/p001", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "product_id" in data and data["product_id"] == "p001":
            log_test("Marketplace: GET /products/{id} returns single product", True)
        else:
            log_test("Marketplace: GET /products/{id} returns single product", False, "Wrong product")
    else:
        log_test("Marketplace: GET /products/{id} returns single product", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Marketplace: GET /products/{id} returns single product", False, str(e))

# 5.5 POST /orders
try:
    resp = requests.post(f"{BASE_URL}/orders",
                        headers={"Authorization": f"Bearer {customer_a_token}"},
                        json={
                            "items": [{"product_id": "p001", "quantity": 2}],
                            "address": "Auckland"
                        },
                        timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "order_id" in data and "total" in data:
            # p001 is Mitsubishi 5kW Heat Pump at $2499, so 2 * 2499 = 4998
            expected_total = 2499.0 * 2
            if abs(data["total"] - expected_total) < 1:
                log_test("Marketplace: POST /orders computes total correctly (~$4998)", True)
            else:
                log_test("Marketplace: POST /orders computes total correctly (~$4998)", False, 
                        f"Expected ~{expected_total}, got {data['total']}")
        else:
            log_test("Marketplace: POST /orders computes total correctly (~$4998)", False, "Missing order_id or total")
    else:
        log_test("Marketplace: POST /orders computes total correctly (~$4998)", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Marketplace: POST /orders computes total correctly (~$4998)", False, str(e))

# 5.6 GET /orders/mine
try:
    resp = requests.get(f"{BASE_URL}/orders/mine",
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            log_test("Marketplace: GET /orders/mine returns orders", True)
        else:
            log_test("Marketplace: GET /orders/mine returns orders", False, "Empty response")
    else:
        log_test("Marketplace: GET /orders/mine returns orders", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Marketplace: GET /orders/mine returns orders", False, str(e))

# ============================================================================
# 6. FEED TESTS (MEDIUM PRIORITY)
# ============================================================================
print("\n📰 TESTING FEED ENDPOINTS\n")

post_id = None

# 6.1 GET /feed (should return >=6 seeded posts)
try:
    resp = requests.get(f"{BASE_URL}/feed", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) >= 6:
            log_test("Feed: GET /feed returns >=6 seeded posts", True)
        else:
            log_test("Feed: GET /feed returns >=6 seeded posts", False, f"Only {len(data)} posts")
    else:
        log_test("Feed: GET /feed returns >=6 seeded posts", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Feed: GET /feed returns >=6 seeded posts", False, str(e))

# 6.2 GET /feed?post_type=sale
try:
    resp = requests.get(f"{BASE_URL}/feed?post_type=sale", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            all_sale = all(p.get("post_type") == "sale" for p in data)
            if all_sale:
                log_test("Feed: GET /feed?post_type=sale filters correctly", True)
            else:
                log_test("Feed: GET /feed?post_type=sale filters correctly", False, "Wrong post_type in results")
        else:
            log_test("Feed: GET /feed?post_type=sale filters correctly", False, "Empty response")
    else:
        log_test("Feed: GET /feed?post_type=sale filters correctly", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Feed: GET /feed?post_type=sale filters correctly", False, str(e))

# 6.3 POST /feed (as Provider B)
try:
    resp = requests.post(f"{BASE_URL}/feed",
                        headers={"Authorization": f"Bearer {provider_b_token}"},
                        json={
                            "title": "Test Post from Provider B",
                            "content": "This is a test post to verify feed creation",
                            "post_type": "news",
                            "tags": ["test", "automation"]
                        },
                        timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "post_id" in data:
            post_id = data["post_id"]
            log_test("Feed: POST /feed creates post", True)
        else:
            log_test("Feed: POST /feed creates post", False, "No post_id")
    else:
        log_test("Feed: POST /feed creates post", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Feed: POST /feed creates post", False, str(e))

# 6.4 POST /feed/{post_id}/like (toggle like)
if post_id:
    try:
        resp = requests.post(f"{BASE_URL}/feed/{post_id}/like",
                            headers={"Authorization": f"Bearer {customer_a_token}"},
                            timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if "likes" in data and "liked" in data:
                log_test("Feed: POST /feed/{id}/like toggles like", True)
            else:
                log_test("Feed: POST /feed/{id}/like toggles like", False, "Missing likes or liked")
        else:
            log_test("Feed: POST /feed/{id}/like toggles like", False, f"Status {resp.status_code}")
    except Exception as e:
        log_test("Feed: POST /feed/{id}/like toggles like", False, str(e))

# ============================================================================
# 7. PROPERTIES TESTS (MEDIUM PRIORITY)
# ============================================================================
print("\n🏠 TESTING PROPERTIES ENDPOINTS\n")

property_id = None

# 7.1 POST /properties
try:
    resp = requests.post(f"{BASE_URL}/properties",
                        headers={"Authorization": f"Bearer {customer_a_token}"},
                        json={
                            "address": "1 Test Rd, Auckland",
                            "property_type": "residential",
                            "bedrooms": 3
                        },
                        timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "property_id" in data:
            property_id = data["property_id"]
            log_test("Properties: POST /properties creates property", True)
        else:
            log_test("Properties: POST /properties creates property", False, "No property_id")
    else:
        log_test("Properties: POST /properties creates property", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Properties: POST /properties creates property", False, str(e))

# 7.2 GET /properties/mine
try:
    resp = requests.get(f"{BASE_URL}/properties/mine",
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            found = any(p.get("property_id") == property_id for p in data)
            if found:
                log_test("Properties: GET /properties/mine returns property", True)
            else:
                log_test("Properties: GET /properties/mine returns property", False, "Property not found")
        else:
            log_test("Properties: GET /properties/mine returns property", False, "Empty response")
    else:
        log_test("Properties: GET /properties/mine returns property", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Properties: GET /properties/mine returns property", False, str(e))

# 7.3 DELETE /properties/{property_id}
if property_id:
    try:
        resp = requests.delete(f"{BASE_URL}/properties/{property_id}",
                              headers={"Authorization": f"Bearer {customer_a_token}"},
                              timeout=10)
        
        if resp.status_code == 200:
            log_test("Properties: DELETE /properties/{id} deletes property", True)
        else:
            log_test("Properties: DELETE /properties/{id} deletes property", False, f"Status {resp.status_code}")
    except Exception as e:
        log_test("Properties: DELETE /properties/{id} deletes property", False, str(e))

# ============================================================================
# 8. PROVIDERS TESTS (MEDIUM PRIORITY)
# ============================================================================
print("\n👷 TESTING PROVIDERS ENDPOINTS\n")

# 8.1 GET /providers/nearby (should return 9+ seeded providers)
try:
    resp = requests.get(f"{BASE_URL}/providers/nearby", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) >= 9:
            # Check if providers have lat/lng
            has_coords = all("latitude" in p and "longitude" in p for p in data)
            if has_coords:
                log_test("Providers: GET /providers/nearby returns 9+ with lat/lng", True)
            else:
                log_test("Providers: GET /providers/nearby returns 9+ with lat/lng", False, "Missing coordinates")
        else:
            log_test("Providers: GET /providers/nearby returns 9+ with lat/lng", False, f"Only {len(data)} providers")
    else:
        log_test("Providers: GET /providers/nearby returns 9+ with lat/lng", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Providers: GET /providers/nearby returns 9+ with lat/lng", False, str(e))

# 8.2 GET /providers/nearby?category=plumbing
try:
    resp = requests.get(f"{BASE_URL}/providers/nearby?category=plumbing", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            # Check if all have plumbing in categories
            all_plumbing = all("plumbing" in p.get("categories", []) for p in data)
            if all_plumbing:
                log_test("Providers: GET /providers/nearby?category=plumbing filters", True)
            else:
                log_test("Providers: GET /providers/nearby?category=plumbing filters", False, "Wrong category")
        else:
            log_test("Providers: GET /providers/nearby?category=plumbing filters", False, "Empty response")
    else:
        log_test("Providers: GET /providers/nearby?category=plumbing filters", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Providers: GET /providers/nearby?category=plumbing filters", False, str(e))

# 8.3 GET /providers/me (as Provider B)
try:
    resp = requests.get(f"{BASE_URL}/providers/me",
                       headers={"Authorization": f"Bearer {provider_b_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "user_id" in data and data["user_id"] == provider_b_id:
            log_test("Providers: GET /providers/me returns profile", True)
        else:
            log_test("Providers: GET /providers/me returns profile", False, "Wrong user_id")
    else:
        log_test("Providers: GET /providers/me returns profile", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Providers: GET /providers/me returns profile", False, str(e))

# 8.4 PATCH /providers/me
try:
    resp = requests.patch(f"{BASE_URL}/providers/me",
                         headers={"Authorization": f"Bearer {provider_b_token}"},
                         json={
                             "online": True,
                             "hourly_rate": 95
                         },
                         timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("online") == True and data.get("hourly_rate") == 95:
            log_test("Providers: PATCH /providers/me updates profile", True)
        else:
            log_test("Providers: PATCH /providers/me updates profile", False, "Values not updated")
    else:
        log_test("Providers: PATCH /providers/me updates profile", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Providers: PATCH /providers/me updates profile", False, str(e))

# ============================================================================
# 9. STATS TESTS (MEDIUM PRIORITY)
# ============================================================================
print("\n📊 TESTING STATS ENDPOINTS\n")

# 9.1 GET /stats/customer
try:
    resp = requests.get(f"{BASE_URL}/stats/customer",
                       headers={"Authorization": f"Bearer {customer_a_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        required_fields = ["total_spent", "jobs_done", "active_jobs", "upcoming", "unpaid", "avg_cost"]
        has_all = all(field in data for field in required_fields)
        if has_all:
            log_test("Stats: GET /stats/customer returns all fields", True)
        else:
            missing = [f for f in required_fields if f not in data]
            log_test("Stats: GET /stats/customer returns all fields", False, f"Missing: {missing}")
    else:
        log_test("Stats: GET /stats/customer returns all fields", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Stats: GET /stats/customer returns all fields", False, str(e))

# 9.2 GET /stats/provider
try:
    resp = requests.get(f"{BASE_URL}/stats/provider",
                       headers={"Authorization": f"Bearer {provider_b_token}"},
                       timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        required_fields = ["earnings", "jobs_done", "active_jobs", "pending_bids"]
        has_all = all(field in data for field in required_fields)
        if has_all:
            log_test("Stats: GET /stats/provider returns all fields", True)
        else:
            missing = [f for f in required_fields if f not in data]
            log_test("Stats: GET /stats/provider returns all fields", False, f"Missing: {missing}")
    else:
        log_test("Stats: GET /stats/provider returns all fields", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Stats: GET /stats/provider returns all fields", False, str(e))

# ============================================================================
# 10. CATEGORIES TEST
# ============================================================================
print("\n📋 TESTING CATEGORIES ENDPOINT\n")

# 10.1 GET /categories (should return 12 categories)
try:
    resp = requests.get(f"{BASE_URL}/categories", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) == 12:
            # Check if each has required fields
            has_structure = all("id" in c and "name" in c for c in data)
            if has_structure:
                log_test("Categories: GET /categories returns 12 category objects", True)
            else:
                log_test("Categories: GET /categories returns 12 category objects", False, "Missing fields")
        else:
            log_test("Categories: GET /categories returns 12 category objects", False, f"Expected 12, got {len(data)}")
    else:
        log_test("Categories: GET /categories returns 12 category objects", False, f"Status {resp.status_code}")
except Exception as e:
    log_test("Categories: GET /categories returns 12 category objects", False, str(e))

# ============================================================================
# PRINT SUMMARY
# ============================================================================
print_summary()
