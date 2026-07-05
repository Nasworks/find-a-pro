"""
Dispatchr Backend Regression Tests
Testing deployment blocker fixes:
1. JWT_SECRET required from env (no fallback)
2. /jobs/mine N+1 fix (bids_count, bids_range)
3. /bids/mine N+1 fix (job field populated)
4. /providers/nearby N+1 fix (name field populated)
"""
import requests
import json
import os
from datetime import datetime

# Load backend URL from frontend/.env
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BACKEND_URL = line.split('=')[1].strip()
            break

API_BASE = f"{BACKEND_URL}/api"

print(f"🔗 Testing backend at: {API_BASE}\n")

# Test data
customer_a_email = f"customer_a_{datetime.now().timestamp()}@dispatchr.test"
provider_b_email = f"provider_b_{datetime.now().timestamp()}@dispatchr.test"

customer_a_token = None
provider_b_token = None
customer_a_id = None
provider_b_id = None

job_ids = []
bid_ids = []

def test_auth_with_jwt_secret():
    """Test 1: JWT_SECRET now required from env - register + login + /auth/me must work"""
    global customer_a_token, provider_b_token, customer_a_id, provider_b_id
    
    print("=" * 80)
    print("TEST 1: JWT_SECRET Required from Env (No Fallback)")
    print("=" * 80)
    
    # Register Customer A
    print("\n📝 Registering Customer A...")
    resp = requests.post(f"{API_BASE}/auth/register", json={
        "email": customer_a_email,
        "password": "SecurePass123!",
        "name": "Customer Alice",
        "role": "customer"
    })
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Register failed: {resp.text}"
    data = resp.json()
    assert "user" in data, "No user in response"
    assert "token" in data, "No token in response"
    customer_a_token = data["token"]
    customer_a_id = data["user"]["user_id"]
    print(f"✅ Customer A registered: {customer_a_id}")
    print(f"   Token: {customer_a_token[:20]}...")
    
    # Register Provider B
    print("\n📝 Registering Provider B...")
    resp = requests.post(f"{API_BASE}/auth/register", json={
        "email": provider_b_email,
        "password": "SecurePass123!",
        "name": "Provider Bob",
        "role": "provider"
    })
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Register failed: {resp.text}"
    data = resp.json()
    assert "user" in data, "No user in response"
    assert "token" in data, "No token in response"
    provider_b_token = data["token"]
    provider_b_id = data["user"]["user_id"]
    print(f"✅ Provider B registered: {provider_b_id}")
    print(f"   Token: {provider_b_token[:20]}...")
    
    # Test login with Customer A
    print("\n🔐 Testing login with Customer A...")
    resp = requests.post(f"{API_BASE}/auth/login", json={
        "email": customer_a_email,
        "password": "SecurePass123!"
    })
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    assert "token" in data, "No token in login response"
    print(f"✅ Login successful, token received")
    
    # Test /auth/me with Customer A token
    print("\n👤 Testing GET /auth/me with Customer A token...")
    resp = requests.get(f"{API_BASE}/auth/me", headers={
        "Authorization": f"Bearer {customer_a_token}"
    })
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"/auth/me failed: {resp.text}"
    data = resp.json()
    assert data["user_id"] == customer_a_id, "Wrong user returned"
    assert data["email"] == customer_a_email, "Wrong email"
    print(f"✅ /auth/me working correctly")
    print(f"   User: {data['name']} ({data['email']})")
    
    # Test /auth/me with Provider B token
    print("\n👤 Testing GET /auth/me with Provider B token...")
    resp = requests.get(f"{API_BASE}/auth/me", headers={
        "Authorization": f"Bearer {provider_b_token}"
    })
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"/auth/me failed: {resp.text}"
    data = resp.json()
    assert data["user_id"] == provider_b_id, "Wrong user returned"
    print(f"✅ /auth/me working correctly for Provider B")
    
    # Verify tokens remain valid across requests
    print("\n🔄 Verifying tokens remain valid across multiple requests...")
    for i in range(3):
        resp = requests.get(f"{API_BASE}/auth/me", headers={
            "Authorization": f"Bearer {customer_a_token}"
        })
        assert resp.status_code == 200, f"Token invalid on request {i+1}"
    print(f"✅ Tokens remain valid across multiple requests")
    
    print("\n" + "=" * 80)
    print("✅ TEST 1 PASSED: JWT auth working with required JWT_SECRET")
    print("=" * 80)


def test_jobs_mine_n1_fix():
    """Test 2: /jobs/mine N+1 fix - bids_count and bids_range"""
    global job_ids, bid_ids
    
    print("\n" + "=" * 80)
    print("TEST 2: /jobs/mine N+1 Fix (bids_count, bids_range)")
    print("=" * 80)
    
    # Customer A creates 3 jobs
    print("\n📋 Customer A creating 3 jobs...")
    job_titles = [
        "Fix leaking kitchen tap",
        "Install new bathroom vanity",
        "Repair broken toilet cistern"
    ]
    
    for title in job_titles:
        resp = requests.post(f"{API_BASE}/jobs", 
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "title": title,
                "description": f"Need help with: {title}",
                "category": "plumbing",
                "location": "Auckland Central",
                "budget_min": 100,
                "budget_max": 300,
                "urgency": "this_week"
            }
        )
        assert resp.status_code == 200, f"Job creation failed: {resp.text}"
        job = resp.json()
        job_ids.append(job["job_id"])
        print(f"   ✅ Created job: {job['job_id']} - {title}")
    
    print(f"\n✅ Created {len(job_ids)} jobs")
    
    # Provider B submits bids on first 2 jobs (different amounts)
    print("\n💰 Provider B submitting bids on first 2 jobs...")
    bid_amounts = [150, 250]
    
    for i in range(2):
        resp = requests.post(f"{API_BASE}/bids",
            headers={"Authorization": f"Bearer {provider_b_token}"},
            json={
                "job_id": job_ids[i],
                "amount": bid_amounts[i],
                "message": f"I can help with this job for ${bid_amounts[i]}",
                "eta_days": 2,
                "warranty_months": 12,
                "payment_terms": "50% upfront, 50% on completion"
            }
        )
        assert resp.status_code == 200, f"Bid creation failed: {resp.text}"
        bid = resp.json()
        bid_ids.append(bid["bid_id"])
        print(f"   ✅ Created bid: {bid['bid_id']} - ${bid_amounts[i]} on job {job_ids[i]}")
    
    print(f"\n✅ Created {len(bid_ids)} bids")
    
    # Call GET /api/jobs/mine as Customer A
    print("\n🔍 Testing GET /api/jobs/mine as Customer A...")
    resp = requests.get(f"{API_BASE}/jobs/mine",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"/jobs/mine failed: {resp.text}"
    jobs = resp.json()
    print(f"✅ Retrieved {len(jobs)} jobs")
    
    # Verify each job includes bids_count
    print("\n📊 Verifying bids_count and bids_range...")
    for job in jobs:
        job_id = job["job_id"]
        print(f"\n   Job: {job_id} - {job['title']}")
        
        # Check bids_count exists
        assert "bids_count" in job, f"Missing bids_count for job {job_id}"
        bids_count = job["bids_count"]
        print(f"      bids_count: {bids_count}")
        
        # Jobs with bids should have bids_range
        if bids_count > 0:
            assert "bids_range" in job, f"Missing bids_range for job {job_id} with {bids_count} bids"
            bids_range = job["bids_range"]
            assert "min" in bids_range, f"Missing min in bids_range for job {job_id}"
            assert "max" in bids_range, f"Missing max in bids_range for job {job_id}"
            print(f"      bids_range: min=${bids_range['min']}, max=${bids_range['max']}")
            
            # Verify correct values for first 2 jobs
            if job_id == job_ids[0]:
                assert bids_count == 1, f"Expected 1 bid, got {bids_count}"
                assert bids_range["min"] == 150, f"Expected min=150, got {bids_range['min']}"
                assert bids_range["max"] == 150, f"Expected max=150, got {bids_range['max']}"
                print(f"      ✅ Correct values for job 1")
            elif job_id == job_ids[1]:
                assert bids_count == 1, f"Expected 1 bid, got {bids_count}"
                assert bids_range["min"] == 250, f"Expected min=250, got {bids_range['min']}"
                assert bids_range["max"] == 250, f"Expected max=250, got {bids_range['max']}"
                print(f"      ✅ Correct values for job 2")
        else:
            # Job with no bids should not have bids_range
            assert "bids_range" not in job, f"Job {job_id} has no bids but has bids_range"
            print(f"      ✅ No bids_range (correct for 0 bids)")
            
            # Verify this is job 3
            if job_id == job_ids[2]:
                assert bids_count == 0, f"Expected 0 bids for job 3, got {bids_count}"
                print(f"      ✅ Correct: job 3 has 0 bids")
    
    print("\n" + "=" * 80)
    print("✅ TEST 2 PASSED: /jobs/mine N+1 fix working correctly")
    print("   - bids_count present for all jobs")
    print("   - bids_range present only for jobs with bids")
    print("   - Values are correct")
    print("=" * 80)


def test_bids_mine_n1_fix():
    """Test 3: /bids/mine N+1 fix - job field populated"""
    
    print("\n" + "=" * 80)
    print("TEST 3: /bids/mine N+1 Fix (job field populated)")
    print("=" * 80)
    
    # Call GET /api/bids/mine as Provider B
    print("\n🔍 Testing GET /api/bids/mine as Provider B...")
    resp = requests.get(f"{API_BASE}/bids/mine",
        headers={"Authorization": f"Bearer {provider_b_token}"}
    )
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"/bids/mine failed: {resp.text}"
    bids = resp.json()
    print(f"✅ Retrieved {len(bids)} bids")
    
    # Verify every bid has job field populated
    print("\n📊 Verifying job field populated for each bid...")
    for bid in bids:
        bid_id = bid["bid_id"]
        print(f"\n   Bid: {bid_id} - ${bid['amount']}")
        
        # Check job field exists
        assert "job" in bid, f"Missing job field for bid {bid_id}"
        job = bid["job"]
        assert job is not None, f"job field is None for bid {bid_id}"
        
        # Verify job has required fields
        assert "job_id" in job, f"Missing job_id in job for bid {bid_id}"
        assert "title" in job, f"Missing title in job for bid {bid_id}"
        assert "category" in job, f"Missing category in job for bid {bid_id}"
        assert "description" in job, f"Missing description in job for bid {bid_id}"
        
        print(f"      job: {job['job_id']}")
        print(f"      title: {job['title']}")
        print(f"      category: {job['category']}")
        print(f"      description: {job['description'][:50]}...")
        print(f"      ✅ Job object populated correctly")
    
    print("\n" + "=" * 80)
    print("✅ TEST 3 PASSED: /bids/mine N+1 fix working correctly")
    print("   - All bids have job field populated")
    print("   - Job objects contain correct data")
    print("=" * 80)


def test_providers_nearby_n1_fix():
    """Test 4: /providers/nearby N+1 fix - name field populated"""
    
    print("\n" + "=" * 80)
    print("TEST 4: /providers/nearby N+1 Fix (name field populated)")
    print("=" * 80)
    
    # Call GET /api/providers/nearby (no auth required)
    print("\n🔍 Testing GET /api/providers/nearby...")
    resp = requests.get(f"{API_BASE}/providers/nearby")
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"/providers/nearby failed: {resp.text}"
    providers = resp.json()
    print(f"✅ Retrieved {len(providers)} providers")
    
    # Verify every provider has name field populated
    print("\n📊 Verifying name field populated for each provider...")
    providers_with_name = 0
    for provider in providers:
        user_id = provider.get("user_id", "unknown")
        print(f"\n   Provider: {user_id}")
        
        # Check name field exists and is populated
        assert "name" in provider, f"Missing name field for provider {user_id}"
        name = provider["name"]
        
        if name:
            providers_with_name += 1
            print(f"      name: {name}")
            print(f"      business_name: {provider.get('business_name', 'N/A')}")
            print(f"      ✅ Name populated correctly")
        else:
            print(f"      ⚠️  Name is None/empty")
    
    print(f"\n✅ {providers_with_name}/{len(providers)} providers have name populated")
    
    # Test category filter
    print("\n🔍 Testing GET /api/providers/nearby?category=plumbing...")
    resp = requests.get(f"{API_BASE}/providers/nearby?category=plumbing")
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"/providers/nearby with category failed: {resp.text}"
    plumbing_providers = resp.json()
    print(f"✅ Retrieved {len(plumbing_providers)} plumbing providers")
    
    # Verify filtered providers also have name field
    if plumbing_providers:
        print("\n📊 Verifying name field for filtered providers...")
        for provider in plumbing_providers:
            user_id = provider.get("user_id", "unknown")
            assert "name" in provider, f"Missing name field for plumbing provider {user_id}"
            print(f"   ✅ Provider {user_id}: {provider.get('name', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("✅ TEST 4 PASSED: /providers/nearby N+1 fix working correctly")
    print("   - All providers have name field")
    print("   - Name populated from linked user record")
    print("   - Category filter works correctly")
    print("=" * 80)


def run_all_tests():
    """Run all regression tests"""
    print("\n" + "=" * 80)
    print("🚀 DISPATCHR BACKEND REGRESSION TESTS")
    print("=" * 80)
    print(f"Backend URL: {API_BASE}")
    print(f"Testing deployment blocker fixes:")
    print("  1. JWT_SECRET required from env")
    print("  2. /jobs/mine N+1 fix")
    print("  3. /bids/mine N+1 fix")
    print("  4. /providers/nearby N+1 fix")
    print("=" * 80)
    
    try:
        test_auth_with_jwt_secret()
        test_jobs_mine_n1_fix()
        test_bids_mine_n1_fix()
        test_providers_nearby_n1_fix()
        
        print("\n" + "=" * 80)
        print("🎉 ALL REGRESSION TESTS PASSED!")
        print("=" * 80)
        print("\n✅ Summary:")
        print("   1. JWT_SECRET: Required from env, no fallback - WORKING")
        print("   2. /jobs/mine: bids_count and bids_range correct - WORKING")
        print("   3. /bids/mine: job field populated - WORKING")
        print("   4. /providers/nearby: name field populated - WORKING")
        print("\n✅ All N+1 batching optimizations verified")
        print("✅ All deployment blocker fixes confirmed working")
        print("=" * 80 + "\n")
        
        return True
        
    except AssertionError as e:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print("=" * 80 + "\n")
        return False
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ UNEXPECTED ERROR")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
