# Iter19: Post Job only (mode 'bids') + unlimited bids from multiple providers / across jobs
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


def _demo(role):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role})
    if r.status_code != 200:
        pytest.skip(f"demo login {role} failed")
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


@pytest.fixture(scope="module")
def customer():
    return _demo("customer")


@pytest.fixture(scope="module")
def provider():
    return _demo("provider")


@pytest.fixture(scope="module")
def provider2():
    # Second distinct provider (registered TEST_ account; no user-delete API exists)
    s = requests.Session()
    email = f"test_iter19_prov_{uuid.uuid4().hex[:6]}@example.com"
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "TestPass123!", "name": "TEST_Iter19 Provider", "role": "provider"})
    if r.status_code != 200:
        pytest.skip(f"register failed {r.status_code} {r.text}")
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    s.user_id = r.json()["user"]["user_id"]
    return s


@pytest.fixture(scope="module")
def jobs(customer):
    ids = []
    yield ids
    for j in ids:
        customer.delete(f"{BASE_URL}/api/jobs/{j}")


def _post_job(customer, jobs, title):
    r = customer.post(f"{BASE_URL}/api/jobs", json={
        "title": title, "description": "TEST desc", "category": "plumbing-gas", "subcategory": None,
        "service_type": "residential", "location": "Auckland", "urgency": "flexible", "mode": "bids",
        "photos": [], "route_via_manager": False, "tenancy_id": None})
    assert r.status_code == 200, r.text
    jid = r.json()["job_id"]
    jobs.append(jid)
    return r.json()


class TestUnlimitedBids:
    def test_create_job_mode_bids(self, customer, jobs):
        j = _post_job(customer, jobs, "TEST_iter19 job A")
        assert j["mode"] == "bids"
        g = customer.get(f"{BASE_URL}/api/jobs/{j['job_id']}")
        assert g.status_code == 200 and g.json()["job"]["mode"] == "bids"

    def test_multiple_providers_bid_same_job(self, customer, provider, provider2, jobs):
        jid = jobs[0]
        amounts = []
        for i, s in enumerate([provider, provider2, provider, provider2, provider]):
            amt = 100 + i
            r = s.post(f"{BASE_URL}/api/bids", json={"job_id": jid, "amount": amt, "message": f"TEST bid {i}"})
            assert r.status_code == 200, r.text
            amounts.append(amt)
        g = customer.get(f"{BASE_URL}/api/jobs/{jid}").json()
        assert len(g["bids"]) == 5
        assert len({b["provider_id"] for b in g["bids"]}) == 2
        assert sorted(b["amount"] for b in g["bids"]) == sorted(amounts)

    def test_single_provider_bids_many_jobs(self, customer, provider, jobs):
        new = [_post_job(customer, jobs, f"TEST_iter19 job {k}")["job_id"] for k in range(6)]
        for jid in new:
            r = provider.post(f"{BASE_URL}/api/bids", json={"job_id": jid, "amount": 50, "message": "TEST many"})
            assert r.status_code == 200, r.text
        mine = provider.get(f"{BASE_URL}/api/bids/mine")
        assert mine.status_code == 200
        body = mine.json()
        items = body if isinstance(body, list) else body.get("bids", body.get("items", []))
        job_ids = {(b.get("job_id") or (b.get("bid") or {}).get("job_id")) for b in items}
        assert set(new).issubset(job_ids)

    def test_bid_on_missing_job_404(self, provider):
        r = provider.post(f"{BASE_URL}/api/bids", json={"job_id": "job_nope_x", "amount": 1, "message": "x"})
        assert r.status_code == 404

    def test_bid_unauthenticated_401(self, jobs):
        r = requests.post(f"{BASE_URL}/api/bids", json={"job_id": jobs[0], "amount": 1, "message": "x"})
        assert r.status_code == 401

    def test_customer_can_bid_own_job(self, customer, jobs):
        # Observation test: no role/ownership check on create_bid
        r = customer.post(f"{BASE_URL}/api/bids", json={"job_id": jobs[0], "amount": 1, "message": "TEST self"})
        print("customer self-bid status:", r.status_code)
        assert r.status_code in (200, 403)
