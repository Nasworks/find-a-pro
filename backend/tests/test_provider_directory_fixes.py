"""Tests for iteration 11 fixes: image URLs, empty-provider gate."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://next-gen-app-39.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "testpass123"


def _register(role="customer"):
    s = requests.Session()
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": PASSWORD, "name": f"Test {role}",
        "role": role, "phone": "0400000000", "city": "Auckland",
    })
    assert r.status_code == 200, r.text
    return s, email


@pytest.fixture(scope="module")
def customer_session():
    s, _ = _register("customer")
    return s


# --- Image URL check ---
def test_unsplash_fixed_image_returns_200():
    r = requests.head("https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800&q=80", allow_redirects=True)
    assert r.status_code == 200


def _results(session):
    r = session.get(f"{API}/providers/search")
    assert r.status_code == 200
    j = r.json()
    return j.get("results") if isinstance(j, dict) else j


def test_search_returns_9_seeded_providers(customer_session):
    data = _results(customer_session)
    assert isinstance(data, list)
    assert len(data) == 9, f"expected 9 got {len(data)}: {[p.get('business_name') for p in data]}"


def test_seeded_provider_visible(customer_session):
    names = [p.get("business_name") for p in _results(customer_session)]
    assert "Sarah Chen Plumbing" in names
    assert "MP Electrical" in names
    assert "SparkClean Services" in names


def test_all_galleries_have_valid_images(customer_session):
    providers = _results(customer_session)
    broken = []
    for p in providers:
        gallery = p.get("gallery") or []
        assert len(gallery) == 4, f"{p.get('business_name')} has {len(gallery)} gallery images"
        for url in gallery:
            resp = requests.head(url, allow_redirects=True, timeout=15)
            if resp.status_code != 200:
                broken.append((p.get("business_name"), url, resp.status_code))
    assert not broken, f"Broken images: {broken}"


def test_provider_detail_gallery_and_reviews(customer_session):
    providers = _results(customer_session)
    pid = providers[0]["user_id"]
    r2 = customer_session.get(f"{API}/providers/{pid}")
    assert r2.status_code == 200
    data = r2.json()
    gallery = data.get("gallery") or []
    assert len(gallery) == 4
    for url in gallery:
        assert requests.head(url, allow_redirects=True, timeout=15).status_code == 200
    # Reviews present
    reviews = data.get("reviews") or []
    assert isinstance(reviews, list)
    # rate_bucket field
    assert data.get("rate_bucket") in ("low", "medium", "high") or "hourly_rate" in data


def test_empty_provider_gated_out(customer_session):
    before = len(_results(customer_session))
    assert before == 9
    _register("provider")
    after = len(_results(customer_session))
    assert after == 9, f"empty provider leaked into search: count={after}"
