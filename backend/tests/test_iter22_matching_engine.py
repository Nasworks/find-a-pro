"""Iter22: commercial track back, job sizes (pricing_type), matching engine, dispatch queue, award, progress, notifications, onboarding."""
import os
import uuid
import pytest
import requests
from pathlib import Path
from pymongo import MongoClient

for _l in Path("/app/frontend/.env").read_text().splitlines():
    if "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
for _l in Path("/app/backend/.env").read_text().splitlines():
    if "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
DEMO_PRO = "demo_provider_ac7046d0"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CREATED = {"jobs": [], "users": []}


def _login(role):
    s = requests.Session()
    r = s.post(f"{API}/auth/demo-login", json={"role": role})
    if r.status_code != 200:
        pytest.skip(f"demo login {role} failed: {r.text}")
    tok = r.json().get("session_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def customer():
    return _login("customer")


@pytest.fixture(scope="module")
def provider():
    return _login("provider")


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for j in CREATED["jobs"]:
        db.bids.delete_many({"job_id": j})
        db.bookings.delete_many({"job_id": j})
        db.job_matches.delete_many({"job_id": j})
        db.notifications.delete_many({"link": f"/jobs/{j}"})
        db.jobs.delete_one({"job_id": j})
    db.notifications.delete_many({"body": {"$regex": "^TEST_"}})
    for u in CREATED["users"]:
        db.provider_specializations.delete_many({"provider_id": u})
        db.provider_profiles.delete_one({"user_id": u})
        db.user_sessions.delete_many({"user_id": u})
        db.notifications.delete_many({"user_id": u})
        db.users.delete_one({"user_id": u})


def _sarah():
    p = db.provider_profiles.find_one({"business_name": "Sarah Chen Plumbing"})
    return p["user_id"] if p else None


def _post(s, **kw):
    body = {"title": f"TEST_{uuid.uuid4().hex[:6]}", "description": "test", "service_type": "residential",
            "category": "plumbing-gas", "subcategory": "tap-toilet-repairs", "pricing_type": "small_fixed",
            "budget_or_estimate": 150, "location": "1 Queen St, Auckland Central, Auckland"}
    body.update(kw)
    r = s.post(f"{API}/jobs", json=body)
    if r.status_code == 200:
        CREATED["jobs"].append(r.json()["job_id"])
    return r


def _match_pids(job_id):
    return {m["provider_id"] for m in db.job_matches.find({"job_id": job_id})}


# --- Taxonomy (both tracks) ---
class TestTaxonomy:
    def test_residential(self):
        d = requests.get(f"{API}/services/taxonomy/residential").json()
        assert d["total_categories"] == 25

    def test_commercial(self):
        d = requests.get(f"{API}/services/taxonomy/commercial").json()
        assert d["total_categories"] == 18
        cc = {c["id"]: c for c in d["categories"]}["commercial-cleaning"]
        assert cc["name"] == "Commercial Cleaning & Facility Hygiene"
        assert "Commercial Kitchen & Hood Cleaning" in {s["name"] for s in cc["subcategories"]}


# --- Job creation validation ---
class TestCreateJob:
    def test_bad_pricing_type(self, customer):
        assert _post(customer, pricing_type="weird").status_code == 400

    def test_bad_budget(self, customer):
        assert _post(customer, budget_or_estimate=-5).status_code == 400

    def test_bad_date(self, customer):
        assert _post(customer, preferred_date="31/12/2026").status_code == 400

    def test_bad_sub(self, customer):
        assert _post(customer, subcategory="nope").status_code == 400


# --- Matching engine ---
class TestMatching:
    def test_auckland_central_small_fixed(self, customer):
        r = _post(customer)
        assert r.status_code == 200, r.text
        j = r.json()
        pids = _match_pids(j["job_id"])
        assert DEMO_PRO in pids
        assert _sarah() in pids
        assert j["status"] == "matched" and j["matched_count"] == len(pids)
        assert j["client_type"] == "residential" and j["pricing_type"] == "small_fixed"

    def test_christchurch_excludes_sarah(self, customer):
        r = _post(customer, location="5 Cathedral Sq, Christchurch")
        pids = _match_pids(r.json()["job_id"])
        assert DEMO_PRO in pids and _sarah() not in pids

    def test_large_quote_tap_excludes_sarah(self, customer):
        r = _post(customer, pricing_type="large_quote", budget_or_estimate=None)
        pids = _match_pids(r.json()["job_id"])
        assert _sarah() not in pids
        # Demo Trade Co. tap spec also small_fixed+hourly only
        assert DEMO_PRO not in pids
        assert r.json()["status"] == "open"

    def test_commercial_handyman_hourly(self, customer):
        r = _post(customer, service_type="commercial", category="building-maintenance",
                  subcategory="commercial-handyman", pricing_type="hourly", budget_or_estimate=3)
        assert r.status_code == 200, r.text
        assert DEMO_PRO in _match_pids(r.json()["job_id"])


# --- Dispatch queue / award / progress ---
class TestDispatchFlow:
    def test_full_flow(self, customer, provider):
        j = _post(customer, preferred_date="2026-03-01").json()
        jid = j["job_id"]
        mine = provider.get(f"{API}/matches/mine").json()
        m = next(x for x in mine if x["job_id"] == jid)
        assert m["match_status"] == "notified" and "access_notes" not in m["job"]
        assert m["job"]["subcategory_name"] == "Tap & Toilet Repairs"
        # quote not blocked? accept works for small_fixed
        r = provider.post(f"{API}/matches/{m['match_id']}/accept", json={"message": "TEST_hi", "available_from": "2026-03-01"})
        assert r.status_code == 200 and r.json()["match_status"] == "accepted"
        # client sees matches
        jm = customer.get(f"{API}/jobs/{jid}/matches").json()
        assert jm["notified"] >= 2 and jm["responded"] == 1
        # notification for client
        n = customer.get(f"{API}/notifications/mine").json()
        assert any(x["type"] == "match_response" and x["link"] == f"/jobs/{jid}" for x in n["items"])
        # cannot award a notified-only match
        sarah_m = db.job_matches.find_one({"job_id": jid, "provider_id": _sarah()})
        assert customer.post(f"{API}/jobs/{jid}/award", json={"match_id": sarah_m["match_id"]}).status_code == 400
        # provider cannot award
        assert provider.post(f"{API}/jobs/{jid}/award", json={"match_id": m["match_id"]}).status_code == 403
        r = customer.post(f"{API}/jobs/{jid}/award", json={"match_id": m["match_id"]})
        assert r.status_code == 200, r.text
        assert r.json()["amount"] == 150
        job = db.jobs.find_one({"job_id": jid})
        assert job["status"] == "assigned" and job["assigned_provider_id"] == DEMO_PRO
        assert db.job_matches.find_one({"match_id": sarah_m["match_id"]})["match_status"] == "closed"
        assert db.bids.find_one({"job_id": jid, "status": "accepted", "provider_id": DEMO_PRO})
        bk = db.bookings.find_one({"job_id": jid})
        assert bk and bk["scheduled_at"].strftime("%Y-%m-%d") == "2026-03-01"
        # second award rejected
        assert customer.post(f"{API}/jobs/{jid}/award", json={"match_id": m["match_id"]}).status_code == 400
        # provider no longer can respond
        assert provider.post(f"{API}/matches/{m['match_id']}/accept", json={}).status_code == 400
        n = provider.get(f"{API}/notifications/mine").json()
        assert any(x["type"] == "job_awarded" for x in n["items"])
        # progress
        assert provider.post(f"{API}/jobs/{jid}/progress", json={"status": "bogus"}).status_code == 400
        assert provider.post(f"{API}/jobs/{jid}/progress", json={"status": "in_progress"}).json()["status"] == "in_progress"
        assert provider.post(f"{API}/jobs/{jid}/progress", json={"status": "in_progress"}).status_code == 400
        assert provider.post(f"{API}/jobs/{jid}/progress", json={"status": "done"}).json()["status"] == "done"
        assert db.jobs.find_one({"job_id": jid})["status"] == "done"

    def test_large_quote_flow(self, customer, provider):
        j = _post(customer, category="plumbing-gas", subcategory="leak-repairs", pricing_type="large_quote",
                  budget_or_estimate=None, budget_min=500, budget_max=2000).json()
        jid = j["job_id"]
        m = next(x for x in provider.get(f"{API}/matches/mine").json() if x["job_id"] == jid)
        assert provider.post(f"{API}/matches/{m['match_id']}/accept", json={}).status_code == 400
        assert provider.post(f"{API}/matches/{m['match_id']}/quote", json={"amount": 0}).status_code == 400
        r = provider.post(f"{API}/matches/{m['match_id']}/quote", json={"amount": 1234.5, "message": "TEST_q"})
        assert r.status_code == 200 and r.json()["match_status"] == "quote_submitted" and r.json()["quote_amount"] == 1234.5
        r = customer.post(f"{API}/jobs/{jid}/award", json={"match_id": m["match_id"]})
        assert r.status_code == 200 and r.json()["amount"] == 1234.5

    def test_decline(self, customer, provider):
        jid = _post(customer).json()["job_id"]
        m = next(x for x in provider.get(f"{API}/matches/mine").json() if x["job_id"] == jid)
        assert provider.post(f"{API}/matches/{m['match_id']}/decline").status_code == 200
        assert db.job_matches.find_one({"match_id": m["match_id"]})["match_status"] == "declined"
        assert provider.post(f"{API}/matches/{m['match_id']}/accept", json={}).status_code == 400

    def test_other_provider_match_404(self, customer, provider):
        jid = _post(customer).json()["job_id"]
        sm = db.job_matches.find_one({"job_id": jid, "provider_id": _sarah()})
        assert provider.post(f"{API}/matches/{sm['match_id']}/accept", json={}).status_code == 404

    def test_customer_cannot_use_provider_endpoints(self, customer):
        assert customer.get(f"{API}/matches/mine").status_code == 403
        assert customer.get(f"{API}/providers/me/onboarding").status_code == 403

    def test_notifications_read_all(self, customer):
        assert customer.post(f"{API}/notifications/read-all").status_code == 200
        assert customer.get(f"{API}/notifications/mine").json()["unread"] == 0


# --- Regression: board shows matched jobs, classic bid accept ---
class TestRegression:
    def test_board_lists_matched(self, customer, provider):
        jid = _post(customer).json()["job_id"]
        board = provider.get(f"{API}/jobs/board").json()
        assert any(b["job_id"] == jid and b["status"] == "matched" for b in board)

    def test_classic_bid_accept(self, customer, provider):
        jid = _post(customer).json()["job_id"]
        b = provider.post(f"{API}/bids", json={"job_id": jid, "amount": 140, "message": "TEST_bid", "eta_days": 1})
        assert b.status_code == 200, b.text
        r = customer.post(f"{API}/bids/{b.json()['bid_id']}/accept")
        assert r.status_code == 200
        assert db.jobs.find_one({"job_id": jid})["status"] == "in_progress"
        assert db.job_matches.find_one({"job_id": jid, "provider_id": DEMO_PRO})["match_status"] == "awarded"


# --- Onboarding (fresh provider) ---
class TestOnboarding:
    @pytest.fixture(scope="class")
    def fresh(self):
        email = f"test_pro_{uuid.uuid4().hex[:8]}@example.com"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": "TEST_Pro", "role": "provider"})
        if r.status_code != 200:
            pytest.skip(f"register failed {r.status_code} {r.text[:200]}")
        d = r.json()
        uid = (d.get("user") or {}).get("user_id")
        CREATED["users"].append(uid)
        tok = d.get("session_token") or d.get("token")
        if tok:
            s.headers["Authorization"] = f"Bearer {tok}"
        if s.get(f"{API}/auth/me").json().get("role") != "provider":
            s.patch(f"{API}/auth/role", json={"role": "provider"})
        return s

    def _body(self, **kw):
        b = {"business_name": "TEST_Biz", "business_size": "solo", "service_tracks": ["residential"],
             "service_area_suburbs": ["Ponsonby"],
             "specializations": [{"service_type": "residential", "category_id": "plumbing-gas",
                                  "subcategory_id": "tap-toilet-repairs", "pricing_modes": ["small_fixed"], "rate": 90}]}
        b.update(kw)
        return b

    def test_not_onboarded(self, fresh):
        r = fresh.get(f"{API}/providers/me/onboarding")
        assert r.status_code == 200 and r.json()["onboarded"] is False

    def test_invalid(self, fresh):
        u = f"{API}/providers/me/onboarding"
        assert fresh.put(u, json=self._body(specializations=[])).status_code == 400
        assert fresh.put(u, json=self._body(business_name=" ")).status_code == 400
        assert fresh.put(u, json=self._body(business_size="huge")).status_code == 400
        assert fresh.put(u, json=self._body(service_tracks=[])).status_code == 400
        bad = self._body()
        bad["specializations"][0]["subcategory_id"] = "nope"
        assert fresh.put(u, json=bad).status_code == 400
        bad = self._body()
        bad["specializations"][0]["pricing_modes"] = []
        assert fresh.put(u, json=bad).status_code == 400
        bad = self._body(specializations=[{"service_type": "commercial", "category_id": "building-maintenance",
                                           "subcategory_id": "commercial-handyman", "pricing_modes": ["hourly"]}])
        assert fresh.put(u, json=bad).status_code == 400

    def test_save_and_match(self, fresh, customer):
        r = fresh.put(f"{API}/providers/me/onboarding", json=self._body())
        assert r.status_code == 200, r.text
        assert r.json()["onboarded"] is True and len(r.json()["specializations"]) == 1
        jid = _post(customer, location="10 Ponsonby Rd, Ponsonby, Auckland").json()["job_id"]
        me = fresh.get(f"{API}/auth/me").json()["user_id"]
        assert me in _match_pids(jid)

    def test_non_provider_403(self, customer):
        assert customer.put(f"{API}/providers/me/onboarding", json=self._body()).status_code == 403
