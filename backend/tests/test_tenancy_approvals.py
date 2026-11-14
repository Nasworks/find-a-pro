"""Backend tests: tenant → manager tenancy + job approval workflow (2026-02-07)."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://recover-app-6--0t57q2zf.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(role: str, prefix: str):
    ts = uuid.uuid4().hex[:8]
    s = _sess()
    payload = {
        "email": f"qa-{prefix}-{ts}@dispatchr.demo",
        "password": "testpass123",
        "name": f"Test {prefix.title()}",
        "role": role,
    }
    r = s.post(f"{API}/auth/register", json=payload)
    assert r.status_code == 200, f"register {prefix} failed: {r.status_code} {r.text}"
    data = r.json()
    return s, data["user"], payload["email"]


@pytest.fixture(scope="module")
def tina():
    s, user, email = _register("customer", "tina")
    return {"s": s, "user": user, "email": email}


@pytest.fixture(scope="module")
def larry():
    s, user, email = _register("landlord", "larry")
    return {"s": s, "user": user, "email": email}


@pytest.fixture(scope="module")
def pete():
    s, user, email = _register("provider", "pete")
    return {"s": s, "user": user, "email": email}


# ---- Tenancy lifecycle ----
def test_1_tenancy_create_pending(tina, larry):
    r = tina["s"].post(f"{API}/tenancies", json={
        "approver_email": larry["email"],
        "approver_role": "landlord",
        "label": "12 Grey Lynn Ave",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "tenancy_id" in data
    assert data["status"] == "pending"
    assert data["approver_email"] == larry["email"].lower()
    # approver_id should be pre-linked since Larry is registered
    assert data.get("approver_id") == larry["user"]["user_id"]
    tina["tenancy_id"] = data["tenancy_id"]


def test_2_duplicate_tenancy_returns_existing(tina, larry):
    r = tina["s"].post(f"{API}/tenancies", json={
        "approver_email": larry["email"],
        "approver_role": "landlord",
        "label": "again",
    })
    assert r.status_code == 200
    assert r.json()["tenancy_id"] == tina["tenancy_id"]


def test_3_larry_sees_pending_tenancy(tina, larry):
    r = larry["s"].get(f"{API}/tenancies/mine")
    assert r.status_code == 200
    tens = r.json()
    match = [t for t in tens if t["tenancy_id"] == tina["tenancy_id"]]
    assert match, f"Larry didn't see tenancy: {tens}"
    assert match[0]["status"] == "pending"


def test_4_larry_approves_tenancy(tina, larry):
    r = larry["s"].post(f"{API}/tenancies/{tina['tenancy_id']}/approve")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "active"
    assert data["approver_id"] == larry["user"]["user_id"]


def test_5_tina_sees_active(tina):
    r = tina["s"].get(f"{API}/tenancies/mine")
    assert r.status_code == 200
    match = [t for t in r.json() if t["tenancy_id"] == tina["tenancy_id"]]
    assert match and match[0]["status"] == "active"


# ---- Job routing ----
def test_6_post_job_route_via_manager_pending(tina, larry):
    r = tina["s"].post(f"{API}/jobs", json={
        "title": "Leaking tap in kitchen",
        "description": "kitchen sink drip",
        "category": "Plumbing",
        "route_via_manager": True,
    })
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["approval_status"] == "pending"
    assert job["approver_id"] == larry["user"]["user_id"]
    assert job["tenant_id"] == tina["user"]["user_id"]
    assert job["billing_target"] == "approver"
    tina["job1_id"] = job["job_id"]


def test_7_provider_board_excludes_pending(pete, tina):
    r = pete["s"].get(f"{API}/jobs/board")
    assert r.status_code == 200
    ids = [j["job_id"] for j in r.json()]
    assert tina["job1_id"] not in ids


def test_8_landlord_approval_queue_has_job(larry, tina):
    r = larry["s"].get(f"{API}/approvals/queue")
    assert r.status_code == 200
    jobs = r.json()
    match = [j for j in jobs if j["job_id"] == tina["job1_id"]]
    assert match, f"job not in queue: {jobs}"
    assert match[0].get("tenant") and match[0]["tenant"]["user_id"] == tina["user"]["user_id"]


def test_9_approve_open_to_bids(larry, pete, tina):
    r = larry["s"].post(f"{API}/jobs/{tina['job1_id']}/approve", json={"open_to_bids": True})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["approval_status"] == "approved"
    assert j["billing_target"] == "approver"
    # Now visible on Pete's board
    r2 = pete["s"].get(f"{API}/jobs/board")
    ids = [x["job_id"] for x in r2.json()]
    assert tina["job1_id"] in ids


def test_10_approve_with_preferred_provider(tina, larry, pete):
    r = tina["s"].post(f"{API}/jobs", json={
        "title": "Blocked drain",
        "description": "drain outside",
        "category": "Plumbing",
        "route_via_manager": True,
    })
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    tina["job2_id"] = job_id
    r2 = larry["s"].post(f"{API}/jobs/{job_id}/approve", json={
        "assigned_provider_id": pete["user"]["user_id"],
        "open_to_bids": False,
    })
    assert r2.status_code == 200, r2.text
    j = r2.json()
    assert j["assigned_provider_id"] == pete["user"]["user_id"]
    assert j["mode"] == "instant"


def test_11_reject_job(tina, larry):
    r = tina["s"].post(f"{API}/jobs", json={
        "title": "Repaint fence",
        "description": "fence",
        "category": "Painting",
        "route_via_manager": True,
    })
    job_id = r.json()["job_id"]
    tina["job3_id"] = job_id
    # empty reason
    r_empty = larry["s"].post(f"{API}/jobs/{job_id}/reject", json={"reason": ""})
    assert r_empty.status_code == 400
    # missing reason (None)
    r_missing = larry["s"].post(f"{API}/jobs/{job_id}/reject", json={})
    assert r_missing.status_code == 400
    # valid reason
    r_ok = larry["s"].post(f"{API}/jobs/{job_id}/reject", json={"reason": "Not urgent, budget on hold"})
    assert r_ok.status_code == 200
    # verify stored
    r_get = tina["s"].get(f"{API}/jobs/{job_id}")
    j = r_get.json()["job"]
    assert j["approval_status"] == "rejected"
    assert j["status"] == "cancelled"
    assert j["rejection_reason"] == "Not urgent, budget on hold"


def test_12_non_approver_cannot_approve(pete, tina, larry):
    # Create a fresh pending job
    r = tina["s"].post(f"{API}/jobs", json={
        "title": "Clean gutters",
        "description": "leaves",
        "category": "Cleaning",
        "route_via_manager": True,
    })
    job_id = r.json()["job_id"]
    r_bad = pete["s"].post(f"{API}/jobs/{job_id}/approve", json={"open_to_bids": True})
    assert r_bad.status_code == 403
    r_bad2 = pete["s"].post(f"{API}/jobs/{job_id}/reject", json={"reason": "no"})
    assert r_bad2.status_code == 403


def test_13_route_via_manager_no_active_tenancy():
    # Fresh tenant with no tenancy
    s, user, _ = _register("customer", "lonely")
    r = s.post(f"{API}/jobs", json={
        "title": "help",
        "description": "x",
        "category": "Plumbing",
        "route_via_manager": True,
    })
    assert r.status_code == 400


def test_14_tenancy_id_of_another_user(tina):
    s, user, _ = _register("customer", "stranger")
    r = s.post(f"{API}/jobs", json={
        "title": "steal",
        "description": "x",
        "category": "Plumbing",
        "tenancy_id": tina["tenancy_id"],
        "route_via_manager": True,
    })
    assert r.status_code == 400


def test_15_non_approver_role_cannot_see_queue(tina):
    r = tina["s"].get(f"{API}/approvals/queue")
    assert r.status_code == 403


def test_16_direct_post_no_approval(tina):
    r = tina["s"].post(f"{API}/jobs", json={
        "title": "self",
        "description": "own",
        "category": "Plumbing",
        "route_via_manager": False,
    })
    assert r.status_code == 200
    j = r.json()
    assert j["approval_status"] == "not_required"
    assert j["billing_target"] == "client"


def test_17_preferred_providers(larry, pete, tina):
    # First check preferred list — after test_10 nothing accepted yet, so empty for new landlord
    # But we need to create an accepted bid on one of larry's jobs
    # Use job1 which is approved and open to bids
    r = pete["s"].post(f"{API}/bids", json={
        "job_id": tina["job1_id"],
        "amount": 150.0,
        "message": "can do today",
        "eta_days": 1,
    })
    assert r.status_code == 200
    bid_id = r.json()["bid_id"]
    # Tina (job client) accepts
    r_acc = tina["s"].post(f"{API}/bids/{bid_id}/accept")
    assert r_acc.status_code == 200
    # Now Larry's preferred providers should include Pete
    r_pref = larry["s"].get(f"{API}/approvals/preferred-providers")
    assert r_pref.status_code == 200
    ids = [p["user_id"] for p in r_pref.json()]
    assert pete["user"]["user_id"] in ids
