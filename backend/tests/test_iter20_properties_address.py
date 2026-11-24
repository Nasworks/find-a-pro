# Iter20: Saved properties CRUD, address search (OSM/Photon), job property_id + access_notes privacy
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


def _demo(role):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role})
    if r.status_code != 200:
        pytest.skip(f"demo login {role} failed")
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    s.user_id = r.json()["user"]["user_id"]
    return s


@pytest.fixture(scope="module")
def customer():
    return _demo("customer")


@pytest.fixture(scope="module")
def landlord():
    return _demo("landlord")


@pytest.fixture(scope="module")
def provider():
    return _demo("provider")


@pytest.fixture(scope="module")
def created():
    """(session, property_id) pairs and (session, job_id) to clean up."""
    d = {"props": [], "jobs": []}
    yield d
    for s, pid in d["props"]:
        s.delete(f"{BASE_URL}/api/properties/{pid}")
    for s, jid in d["jobs"]:
        s.delete(f"{BASE_URL}/api/jobs/{jid}")


# ---- Address search ----
class TestAddressSearch:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/address/search", params={"q": "Queen Street Auckland"})
        assert r.status_code in (401, 403)

    def test_short_query_empty(self, customer):
        r = customer.get(f"{BASE_URL}/api/address/search", params={"q": "ab"})
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_osm_results(self, customer):
        r = customer.get(f"{BASE_URL}/api/address/search", params={"q": "Queen Street Auckland"}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["source"] == "osm", d
        assert len(d["results"]) > 0
        x = d["results"][0]
        for k in ("id", "main", "secondary", "address", "lat", "lng"):
            assert k in x
        assert isinstance(x["lat"], float) and -48 < x["lat"] < -34

    def test_details_400_without_google(self, customer):
        r = customer.get(f"{BASE_URL}/api/address/details", params={"place_id": "g:abc"})
        assert r.status_code == 400


# ---- Properties CRUD (landlord used; snapshot existing to restore primary) ----
class TestProperties:
    def test_validation(self, customer):
        assert customer.post(f"{BASE_URL}/api/properties", json={"address": "  "}).status_code == 400
        assert customer.post(f"{BASE_URL}/api/properties", json={"address": "TEST_1 X St", "property_type": "industrial"}).status_code == 400
        assert customer.post(f"{BASE_URL}/api/properties", json={"address": "TEST_1 X St", "bedrooms": 101}).status_code == 400
        assert customer.post(f"{BASE_URL}/api/properties", json={"address": "TEST_1 X St", "bathrooms": -1}).status_code == 400
        assert customer.post(f"{BASE_URL}/api/properties", json={}).status_code == 422

    def test_full_lifecycle(self, customer, provider, created):
        before = customer.get(f"{BASE_URL}/api/properties/mine").json()
        orig_primary = next((p["property_id"] for p in before if p["is_primary"]), None)
        # create secondary
        r = customer.post(f"{BASE_URL}/api/properties", json={
            "address": "TEST_10 Queen Street, Auckland", "name": "TEST_Rental", "property_type": "residential",
            "bedrooms": 2, "bathrooms": 1.5, "access_notes": "TEST gate 1234", "lat": -36.85, "lng": 174.76})
        assert r.status_code == 200, r.text
        p = r.json()
        pid = p["property_id"]
        created["props"].append((customer, pid))
        assert p["is_primary"] is (orig_primary is None)
        assert p["bathrooms"] == 1.5 and p["property_type"] == "residential"
        # list contains it, primary first
        lst = customer.get(f"{BASE_URL}/api/properties/mine").json()
        assert any(x["property_id"] == pid for x in lst)
        assert lst[0]["is_primary"] is True
        assert "_id" not in lst[0]
        # patch
        r = customer.patch(f"{BASE_URL}/api/properties/{pid}", json={"name": "TEST_Renamed", "bedrooms": 3})
        assert r.status_code == 200 and r.json()["name"] == "TEST_Renamed" and r.json()["bedrooms"] == 3
        assert customer.patch(f"{BASE_URL}/api/properties/{pid}", json={"property_type": "x"}).status_code == 400
        # other user cannot touch it
        assert provider.patch(f"{BASE_URL}/api/properties/{pid}", json={"name": "hack"}).status_code == 404
        assert provider.post(f"{BASE_URL}/api/properties/{pid}/primary").status_code == 404
        assert provider.delete(f"{BASE_URL}/api/properties/{pid}").status_code in (403, 404)
        # make primary -> only one primary
        assert customer.post(f"{BASE_URL}/api/properties/{pid}/primary").status_code == 200
        lst = customer.get(f"{BASE_URL}/api/properties/mine").json()
        prim = [x for x in lst if x["is_primary"]]
        assert len(prim) == 1 and prim[0]["property_id"] == pid and lst[0]["property_id"] == pid
        # delete primary -> oldest remaining becomes primary
        assert customer.delete(f"{BASE_URL}/api/properties/{pid}").status_code == 200
        created["props"].remove((customer, pid))
        lst = customer.get(f"{BASE_URL}/api/properties/mine").json()
        assert all(x["property_id"] != pid for x in lst)
        if lst:
            prim = [x for x in lst if x["is_primary"]]
            assert len(prim) == 1
            oldest = sorted(lst, key=lambda x: x["created_at"])[0]
            assert prim[0]["property_id"] == oldest["property_id"]
            # restore original primary
            if orig_primary and prim[0]["property_id"] != orig_primary:
                customer.post(f"{BASE_URL}/api/properties/{orig_primary}/primary")

    def test_create_with_is_primary_unsets_others(self, landlord, created):
        before = landlord.get(f"{BASE_URL}/api/properties/mine").json()
        orig_primary = next((p["property_id"] for p in before if p["is_primary"]), None)
        r = landlord.post(f"{BASE_URL}/api/properties", json={"address": "TEST_5 Ponsonby Rd", "is_primary": True})
        assert r.status_code == 200
        pid = r.json()["property_id"]
        created["props"].append((landlord, pid))
        lst = landlord.get(f"{BASE_URL}/api/properties/mine").json()
        assert [x["property_id"] for x in lst if x["is_primary"]] == [pid]
        landlord.delete(f"{BASE_URL}/api/properties/{pid}")
        created["props"].remove((landlord, pid))
        if orig_primary:
            landlord.post(f"{BASE_URL}/api/properties/{orig_primary}/primary")
            lst = landlord.get(f"{BASE_URL}/api/properties/mine").json()
            assert [x["property_id"] for x in lst if x["is_primary"]] == [orig_primary]


# ---- Jobs with property_id ----
def _job_payload(**kw):
    p = {"title": "TEST_Iter20 leaking tap", "description": "TEST", "category": "plumbing",
         "service_type": "residential", "location": "TEST_10 Queen Street, Auckland", "mode": "bids"}
    p.update(kw)
    return p


class TestJobsProperty:
    def test_foreign_property_rejected(self, customer, landlord, created):
        r = landlord.post(f"{BASE_URL}/api/properties", json={"address": "TEST_Landlord Prop"})
        pid = r.json()["property_id"]
        created["props"].append((landlord, pid))
        r = customer.post(f"{BASE_URL}/api/jobs", json=_job_payload(property_id=pid))
        assert r.status_code == 400
        r = customer.post(f"{BASE_URL}/api/jobs", json=_job_payload(property_id="prop_doesnotexist"))
        assert r.status_code == 400

    def test_job_access_notes_privacy(self, customer, provider, created):
        r = customer.post(f"{BASE_URL}/api/properties", json={
            "address": "TEST_22 Access St, Auckland", "access_notes": "TEST_SECRET_GATE_9999", "lat": -36.9, "lng": 174.7})
        pid = r.json()["property_id"]
        created["props"].append((customer, pid))
        r = customer.post(f"{BASE_URL}/api/jobs", json=_job_payload(property_id=pid, route_via_manager=False))
        assert r.status_code == 200, r.text
        job = r.json()
        created["jobs"].append((customer, job["job_id"]))
        assert job["property_id"] == pid
        assert job["access_notes"] == "TEST_SECRET_GATE_9999"
        assert job["location_lat"] == -36.9  # copied from property
        # owner sees notes
        g = customer.get(f"{BASE_URL}/api/jobs/{job['job_id']}").json()["job"]
        assert g.get("access_notes") == "TEST_SECRET_GATE_9999"
        # provider without accepted bid does not
        g = provider.get(f"{BASE_URL}/api/jobs/{job['job_id']}").json()["job"]
        assert "access_notes" not in g
        # board excludes
        board = provider.get(f"{BASE_URL}/api/jobs/board").json()
        bj = next((j for j in board if j["job_id"] == job["job_id"]), None)
        if bj:
            assert "access_notes" not in bj

    def test_bids_mine_does_not_leak_access_notes(self, customer, provider, created):
        r = customer.post(f"{BASE_URL}/api/properties", json={
            "address": "TEST_33 Leak St, Auckland", "access_notes": "TEST_LEAK_CHECK_1111"})
        pid = r.json()["property_id"]
        created["props"].append((customer, pid))
        r = customer.post(f"{BASE_URL}/api/jobs", json=_job_payload(property_id=pid, route_via_manager=False))
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        created["jobs"].append((customer, jid))
        b = provider.post(f"{BASE_URL}/api/bids", json={"job_id": jid, "amount": 150, "message": "TEST bid"})
        assert b.status_code == 200, b.text
        mine = provider.get(f"{BASE_URL}/api/bids/mine").json()
        mb = next(x for x in mine if x["job_id"] == jid)
        assert "access_notes" not in (mb.get("job") or {}) or not mb["job"].get("access_notes"), \
            "Pending bidder sees access_notes via /api/bids/mine"
