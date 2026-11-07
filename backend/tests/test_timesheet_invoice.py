# Timesheet + job invoice regression tests (iteration 15)
import os
import time
from datetime import datetime, timedelta, timezone
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


def login(role):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role})
    if r.status_code != 200:
        pytest.skip(f"demo login {role} failed {r.status_code}")
    return s


@pytest.fixture(scope="module")
def prov():
    return login("provider")


@pytest.fixture(scope="module")
def cust():
    # demo customer account role has drifted (see test_demo_login_role_matches); use a fresh TEST_ customer
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": f"test_ts_cust_{int(time.time()*1000)}@dispatchr.demo", "password": "testpass123",
        "name": "TEST_TS Customer", "role": "customer"})
    if r.status_code not in (200, 201):
        pytest.skip(f"register failed {r.status_code}")
    return s


@pytest.fixture(scope="module")
def ins():
    return login("insurance")


@pytest.fixture(scope="module")
def created_entries():
    return []


@pytest.fixture(scope="module")
def job(cust, prov, created_entries):
    """Fresh job: customer posts, provider bids $300, customer accepts."""
    r = cust.post(f"{BASE_URL}/api/jobs", json={
        "title": f"TEST_TS job {int(time.time())}", "description": "TEST timesheet invoice job",
        "category": "general-home-maintenance", "subcategory": "handyman-services"})
    assert r.status_code in (200, 201), r.text
    jid = r.json()["job_id"]
    b = prov.post(f"{BASE_URL}/api/bids", json={"job_id": jid, "amount": 300, "message": "TEST bid"})
    assert b.status_code in (200, 201), b.text
    bid_id = b.json().get("bid_id")
    a = cust.post(f"{BASE_URL}/api/bids/{bid_id}/accept")
    assert a.status_code == 200, a.text
    yield jid
    for eid in created_entries:
        prov.delete(f"{BASE_URL}/api/timesheets/entries/{eid}")
    cust.delete(f"{BASE_URL}/api/jobs/{jid}")


@pytest.mark.parametrize("role", ["customer", "provider", "property", "landlord", "facilities", "insurance"])
def test_demo_login_role_matches(role):
    r = requests.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == role


class TestTimesheets:
    def test_jobs_list_includes_job(self, prov, job):
        r = prov.get(f"{BASE_URL}/api/timesheets/jobs")
        assert r.status_code == 200
        ids = [j["job_id"] for j in r.json()]
        assert job in ids
        assert all("_id" not in j for j in r.json())

    def test_jobs_list_forbidden_customer(self, cust):
        assert cust.get(f"{BASE_URL}/api/timesheets/jobs").status_code == 403

    def test_start_stop_timer_with_location(self, prov, job, created_entries):
        # ensure none running for self
        for e in prov.get(f"{BASE_URL}/api/timesheets/active").json():
            if e["worker_id"] == e["provider_id"]:
                prov.post(f"{BASE_URL}/api/timesheets/stop/{e['entry_id']}", json={})
        r = prov.post(f"{BASE_URL}/api/timesheets/start", json={"type": "work", "job_id": job, "lat": -36.85, "lng": 174.76})
        assert r.status_code == 200 and r.json()["ok"] is True, r.text
        e = r.json()["entry"]
        created_entries.append(e["entry_id"])
        assert e["started_lat"] == -36.85 and e["job_id"] == job
        dup = prov.post(f"{BASE_URL}/api/timesheets/start", json={"type": "work"})
        assert dup.json().get("error") == "already_running"
        active = prov.get(f"{BASE_URL}/api/timesheets/active").json()
        assert any(a["entry_id"] == e["entry_id"] for a in active)
        time.sleep(2)
        s = prov.post(f"{BASE_URL}/api/timesheets/stop/{e['entry_id']}", json={"lat": -36.86, "lng": 174.77})
        assert s.status_code == 200
        se = s.json()["entry"]
        assert se["ended_at"] and se["ended_lat"] == -36.86

    def test_start_null_location(self, prov, created_entries):
        r = prov.post(f"{BASE_URL}/api/timesheets/start", json={"type": "travel"})
        assert r.status_code == 200 and r.json()["ok"], r.text
        e = r.json()["entry"]
        created_entries.append(e["entry_id"])
        assert e["started_lat"] is None
        prov.post(f"{BASE_URL}/api/timesheets/stop/{e['entry_id']}", json={})

    def test_invalid_type(self, prov):
        assert prov.post(f"{BASE_URL}/api/timesheets/start", json={"type": "bogus"}).status_code == 400

    def test_manual_entries_and_invoice(self, prov, cust, job, created_entries):
        now = datetime.now(timezone.utc)
        def mk(t, mins, **kw):
            r = prov.post(f"{BASE_URL}/api/timesheets/entries", json={
                "type": t, "job_id": job,
                "started_at": (now - timedelta(minutes=mins + 10)).isoformat(),
                "ended_at": (now - timedelta(minutes=10)).isoformat(), **kw})
            assert r.status_code == 200, r.text
            created_entries.append(r.json()["entry_id"])
            return r.json()
        w = mk("work", 120)
        t = mk("travel", 30, fuel_km=20, fuel_cost=12.5)
        nb = mk("work", 60, billable=False)
        assert t["fuel_cost"] == 12.5 and nb["billable"] is False
        inv = cust.get(f"{BASE_URL}/api/jobs/{job}/invoice")
        assert inv.status_code == 200, inv.text
        d = inv.json()
        kinds = [l["kind"] for l in d["lines"]]
        assert kinds[0] == "quote" and d["lines"][0]["amount"] == 300.0
        assert "work" in kinds and "travel" in kinds and "fuel" in kinds
        fuel = [l for l in d["lines"] if l["kind"] == "fuel"][0]
        assert fuel["amount"] == 12.5 and "20" in fuel["description"]
        rate = w["hourly_rate_snapshot"]
        work = [l for l in d["lines"] if l["kind"] == "work"]
        # non-billable 60 min excluded -> labour approx 2h + timer seconds
        assert abs(sum(l["quantity"] for l in work) - 2.0) < 0.05
        assert abs(sum(l["amount"] for l in work) - 2 * rate) < 2
        assert d["subtotal"] == round(sum(l["amount"] for l in d["lines"]), 2)
        assert d["gst"] == round(d["subtotal"] * 0.15, 2)
        assert d["total"] == round(d["subtotal"] + d["gst"], 2)
        # provider gets same totals
        p = prov.get(f"{BASE_URL}/api/jobs/{job}/invoice").json()
        assert p["total"] == d["total"]

    def test_active_entry_excluded_from_invoice(self, prov, job, created_entries):
        before = prov.get(f"{BASE_URL}/api/jobs/{job}/invoice").json()["entries_count"]
        for e in prov.get(f"{BASE_URL}/api/timesheets/active").json():
            if e["worker_id"] == e["provider_id"]:
                prov.post(f"{BASE_URL}/api/timesheets/stop/{e['entry_id']}", json={})
        r = prov.post(f"{BASE_URL}/api/timesheets/start", json={"type": "work", "job_id": job})
        eid = r.json()["entry"]["entry_id"]
        created_entries.append(eid)
        after = prov.get(f"{BASE_URL}/api/jobs/{job}/invoice").json()["entries_count"]
        assert after == before
        prov.post(f"{BASE_URL}/api/timesheets/stop/{eid}", json={})

    def test_invoice_forbidden_insurance(self, ins, job):
        assert ins.get(f"{BASE_URL}/api/jobs/{job}/invoice").status_code == 403

    def test_invoice_404(self, cust):
        assert cust.get(f"{BASE_URL}/api/jobs/job_doesnotexist/invoice").status_code == 404

    def test_delete_entry(self, prov, created_entries):
        now = datetime.now(timezone.utc)
        r = prov.post(f"{BASE_URL}/api/timesheets/entries", json={
            "type": "materials", "started_at": (now - timedelta(minutes=20)).isoformat(), "ended_at": now.isoformat()})
        eid = r.json()["entry_id"]
        assert prov.delete(f"{BASE_URL}/api/timesheets/entries/{eid}").status_code == 200
        ids = [e["entry_id"] for e in prov.get(f"{BASE_URL}/api/timesheets/entries").json()]
        assert eid not in ids
        assert prov.delete(f"{BASE_URL}/api/timesheets/entries/{eid}").status_code == 404

    def test_manual_entry_end_before_start(self, prov, created_entries):
        """Backend should reject ended_at < started_at (validation check)."""
        now = datetime.now(timezone.utc)
        r = prov.post(f"{BASE_URL}/api/timesheets/entries", json={
            "type": "work", "started_at": now.isoformat(), "ended_at": (now - timedelta(hours=1)).isoformat()})
        if r.status_code == 200:
            created_entries.append(r.json()["entry_id"])
        assert r.status_code == 400

    def test_manual_entry_bad_fuel(self, prov, created_entries):
        now = datetime.now(timezone.utc)
        r = prov.post(f"{BASE_URL}/api/timesheets/entries", json={
            "type": "travel", "fuel_km": "abc", "started_at": (now - timedelta(minutes=5)).isoformat(), "ended_at": now.isoformat()})
        if r.status_code == 200:
            created_entries.append(r.json()["entry_id"])
        assert r.status_code in (400, 422)
