"""Iter21: residential-only app - taxonomy merge, commercial removal, keyword detection, DB purge."""
import os
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

NEW_SUBS = {
    "security-smart-home": "Locksmith Services",
    "kitchens-bathrooms-renovations": "Builders & Renovations",
    "concrete-outdoor-construction": "Bricklaying & Masonry",
    "gardening-lawn": "Arborist & Tree Services",
    "carpentry-joinery": "Gates",
    "cleaning": "Pest Control",
    "appliance-installation": "Appliance Repairs",
    "data-communications": "Home IT Support",
}
NEW_CATS = {"building-engineering-inspections", "moving-delivery-rubbish", "home-care-pet-services",
            "tutoring-advisory-professional"}


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
def created():
    d = {"jobs": [], "props": []}
    yield d
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for j in d["jobs"]:
        db.bids.delete_many({"job_id": j})
        db.jobs.delete_one({"job_id": j})
    for p in d["props"]:
        db.properties.delete_one({"property_id": p})


# --- Taxonomy ---
class TestTaxonomy:
    def test_residential_counts_and_new(self):
        r = requests.get(f"{API}/services/taxonomy/residential")
        assert r.status_code == 200
        d = r.json()
        assert d["total_categories"] == 25
        assert d["total_subcategories"] == 179
        by_id = {c["id"]: c for c in d["categories"]}
        assert NEW_CATS <= set(by_id)
        for cid, sub in NEW_SUBS.items():
            assert sub in {s["name"] for s in by_id[cid]["subcategories"]}, (cid, sub)
        assert "Chimney & Duct Cleaning" in {s["name"] for s in by_id["cleaning"]["subcategories"]}

    def test_no_duplicate_subs(self):
        d = requests.get(f"{API}/services/taxonomy/residential").json()
        names = [s["name"].lower() for c in d["categories"] for s in c["subcategories"]]
        dups = {n for n in names if names.count(n) > 1}
        assert not dups, dups
        cat_names = [c["name"] for c in d["categories"]]
        assert len(cat_names) == len(set(cat_names))
        ids = [c["id"] for c in d["categories"]]
        assert len(ids) == len(set(ids))

    def test_no_commercial_words(self):
        d = requests.get(f"{API}/services/taxonomy/residential").json()
        txt = str(d).lower()
        assert "commercial" not in txt

    @pytest.mark.parametrize("path", ["services/taxonomy/commercial", "services/commercial-taxonomy",
                                      "services/commercial-taxonomy/electrical"])
    def test_commercial_endpoints_404(self, path):
        assert requests.get(f"{API}/{path}").status_code == 404


# --- Detect ---
DETECT = [
    ("locked out", "Locksmith Services"),
    ("rats in the roof", "Pest Control"),
    ("need a tutor", "In-Home Tutoring & Music Lessons"),
    ("man with a van", "Man with a Van / Local Movers"),
    ("pre-purchase inspection", "Building & Property Inspections"),
    ("dripping tap", "Tap & Toilet Repairs"),
    ("chimney sweep", "Chimney & Duct Cleaning"),
    ("arborist", "Arborist & Tree Services"),
    ("need a builder for renovation", "Builders & Renovations"),
    ("rubbish removal", "Rubbish & Green Waste Removal"),
]


@pytest.mark.parametrize("text,sub", DETECT)
def test_detect(text, sub):
    r = requests.get(f"{API}/services/detect", params={"text": text})
    assert r.status_code == 200
    m = r.json()["match"]
    assert m and m["subcategory_name"] == sub, (text, m)


# --- Jobs / properties validation ---
class TestJobsProps:
    def test_commercial_job_rejected(self, customer):
        r = customer.post(f"{API}/jobs", json={"title": "TEST_c", "description": "x", "category": "cleaning",
                                               "service_type": "commercial", "location": "Auckland"})
        assert r.status_code == 400

    def test_residential_new_sub_job(self, customer, created):
        r = customer.post(f"{API}/jobs", json={"title": "TEST_pest", "description": "rats", "category": "cleaning",
                                               "subcategory": "pest-control", "service_type": "residential",
                                               "location": "Auckland"})
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        created["jobs"].append(jid)
        j = customer.get(f"{API}/jobs/{jid}").json()["job"]
        assert j["subcategory"] == "pest-control" and j["service_type"] == "residential"

    def test_new_category_job(self, customer, created):
        r = customer.post(f"{API}/jobs", json={"title": "TEST_tutor", "description": "maths", "category": "tutoring-advisory-professional",
                                               "subcategory": "in-home-tutoring-music-lessons", "location": "Auckland"})
        assert r.status_code == 200, r.text
        created["jobs"].append(r.json()["job_id"])

    def test_commercial_property_rejected(self, customer, created):
        r = customer.post(f"{API}/properties", json={"address": "TEST_1 Queen St", "property_type": "commercial"})
        assert r.status_code == 400
        r = customer.post(f"{API}/properties", json={"address": "TEST_1 Queen St", "property_type": "mixed"})
        assert r.status_code == 400
        r = customer.post(f"{API}/properties", json={"address": "TEST_2 Queen St"})
        assert r.status_code == 200
        pid = r.json()["property_id"]
        created["props"].append(pid)
        assert r.json()["property_type"] == "residential"
        assert customer.patch(f"{API}/properties/{pid}", json={"property_type": "commercial"}).status_code == 400
        assert customer.patch(f"{API}/properties/{pid}", json={"name": "TEST_ok"}).status_code == 200


# --- DB state ---
def test_db_no_commercial_data():
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    assert db.jobs.count_documents({"service_type": {"$exists": True, "$ne": "residential"}}) == 0
    assert db.properties.count_documents({"property_type": {"$in": ["commercial", "mixed"]}}) == 0
