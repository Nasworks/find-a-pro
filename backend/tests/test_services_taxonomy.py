"""Backend tests for the new service taxonomy endpoints and expanded job model."""
import os
import time
import pytest
import requests
from pathlib import Path

# Load frontend .env so REACT_APP_BACKEND_URL is available
_env_path = Path("/app/frontend/.env")
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"

# Valid lucide-react icon names used in the taxonomy — spot check a few
LUCIDE_KNOWN = {
    "Home", "Zap", "Droplets", "Wind", "Hammer", "Paintbrush", "Grid3x3",
    "Sparkles", "Layers", "Square", "ShieldCheck", "Router", "Sun", "Waves",
    "Thermometer", "Refrigerator", "HardHat", "Building2", "TreePine", "Flame",
    "Cpu",
}


# ------------------------ taxonomy endpoints ------------------------

def test_commercial_taxonomy():
    r = requests.get(f"{API}/services/commercial-taxonomy")
    assert r.status_code == 200
    data = r.json()
    assert data["total_categories"] == 15
    assert data["total_subcategories"] == 102
    cats = data["categories"]
    assert len(cats) == 15
    for c in cats:
        assert set(c.keys()) >= {"id", "name", "icon", "color", "subcategories"}
        assert c["color"].startswith("#") and len(c["color"]) == 7
        assert isinstance(c["subcategories"], list) and len(c["subcategories"]) > 0
        for s in c["subcategories"]:
            assert set(s.keys()) == {"id", "name"}
        # icon spot-check
        assert c["icon"] in LUCIDE_KNOWN, f"unknown icon: {c['icon']}"


def test_residential_taxonomy():
    r = requests.get(f"{API}/services/residential-taxonomy")
    assert r.status_code == 200
    data = r.json()
    assert data["total_categories"] == 18
    assert data["total_subcategories"] == 122
    assert len(data["categories"]) == 18
    for c in data["categories"]:
        assert c["icon"] in LUCIDE_KNOWN, f"unknown icon: {c['icon']}"


def test_unified_taxonomy_residential():
    r = requests.get(f"{API}/services/taxonomy/residential")
    assert r.status_code == 200
    assert r.json()["total_categories"] == 18


def test_unified_taxonomy_commercial():
    r = requests.get(f"{API}/services/taxonomy/commercial")
    assert r.status_code == 200
    assert r.json()["total_categories"] == 15


def test_unified_taxonomy_invalid():
    r = requests.get(f"{API}/services/taxonomy/invalid")
    assert r.status_code == 404


def test_commercial_category_electrical():
    r = requests.get(f"{API}/services/commercial-taxonomy/electrical")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "electrical"
    assert len(data["subcategories"]) == 8


def test_residential_category_plumbing():
    r = requests.get(f"{API}/services/residential-taxonomy/plumbing-gas")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "plumbing-gas"
    assert len(data["subcategories"]) == 8
    ids = {s["id"] for s in data["subcategories"]}
    assert "blocked-drains" in ids
    assert "leak-repairs" in ids


def test_commercial_category_not_found():
    r = requests.get(f"{API}/services/commercial-taxonomy/does-not-exist")
    assert r.status_code == 404


# ------------------------ legacy /api/categories still works ------------------------

def test_legacy_categories_endpoint():
    r = requests.get(f"{API}/categories")
    assert r.status_code == 200
    data = r.json()
    # Should still return some list (residential-ish categories for legacy consumers)
    assert isinstance(data, list) and len(data) > 0


# ------------------------ jobs with new fields ------------------------

@pytest.fixture(scope="module")
def customer_session():
    s = requests.Session()
    ts = int(time.time())
    email = f"qa-svc-cust-{ts}@dispatchr.demo"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "testpass123",
        "name": "SVC QA Customer", "role": "customer",
    })
    assert r.status_code == 200, r.text
    return s


def test_create_job_residential_with_subcategory(customer_session):
    payload = {
        "title": "TEST_ Fix blocked drain",
        "description": "Kitchen sink drains slowly",
        "category": "plumbing-gas",
        "subcategory": "blocked-drains",
        "service_type": "residential",
        "location": "Auckland",
        "urgency": "flexible",
        "mode": "quotes",
        "photos": [],
    }
    r = customer_session.post(f"{API}/jobs", json=payload)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    # Persist verification
    g = customer_session.get(f"{API}/jobs/{job_id}")
    assert g.status_code == 200
    j = g.json()["job"]
    assert j["category"] == "plumbing-gas"
    assert j["subcategory"] == "blocked-drains"
    assert j["service_type"] == "residential"


def test_create_job_commercial_with_subcategory(customer_session):
    payload = {
        "title": "TEST_ HVAC service",
        "description": "AC not cooling in office",
        "category": "hvac-mechanical",
        "subcategory": "commercial-air-conditioning",
        "service_type": "commercial",
        "location": "Auckland",
        "urgency": "asap",
        "mode": "quotes",
        "photos": [],
    }
    r = customer_session.post(f"{API}/jobs", json=payload)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    j = customer_session.get(f"{API}/jobs/{job_id}").json()["job"]
    assert j["category"] == "hvac-mechanical"
    assert j["subcategory"] == "commercial-air-conditioning"
    assert j["service_type"] == "commercial"


def test_create_job_without_subcategory_still_works(customer_session):
    payload = {
        "title": "TEST_ generic handyman work",
        "description": "Various small odd jobs",
        "category": "general-home-maintenance",
        "service_type": "residential",
        "location": "Auckland",
        "urgency": "flexible",
        "mode": "quotes",
        "photos": [],
    }
    r = customer_session.post(f"{API}/jobs", json=payload)
    assert r.status_code == 200, r.text
    j = customer_session.get(f"{API}/jobs/{r.json()['job_id']}").json()["job"]
    assert j["category"] == "general-home-maintenance"
    assert j.get("subcategory") in (None, "")
    assert j["service_type"] == "residential"
