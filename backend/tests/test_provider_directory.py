"""Tests for provider directory (search, filters, sort, profile)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://recover-app-6--0t57q2zf.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def customer_session():
    s = requests.Session()
    ts = int(time.time() * 1000)
    email = f"qa-customer-{ts}@dispatchr.demo"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "testpass123",
        "name": "QA Customer", "role": "customer",
    })
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def provider_session():
    s = requests.Session()
    ts = int(time.time() * 1000)
    email = f"qa-provider-{ts}@dispatchr.demo"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "testpass123",
        "name": "QA Provider", "role": "provider",
    })
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s


# ---------------- Search / no params ----------------
def test_search_no_params_returns_9(customer_session):
    r = customer_session.get(f"{API}/providers/search")
    assert r.status_code == 200
    body = r.json()
    assert "count" in body and "results" in body
    assert body["count"] == 9, f"expected 9 seeded providers, got {body['count']}"
    # response shape
    first = body["results"][0]
    for k in ["user_id", "business_name", "categories", "hourly_rate", "rating",
              "reviews_count", "jobs_completed", "verified", "rate_bucket"]:
        assert k in first, f"missing key {k}"


# ---------------- Filters ----------------
def test_filter_category_plumbing(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"category": "plumbing"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) >= 1
    names = [p["business_name"] for p in results]
    assert any("Sarah Chen" in n for n in names)
    for p in results:
        assert "plumbing" in p.get("categories", [])


def test_filter_min_rating(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"min_rating": 4.8})
    assert r.status_code == 200
    results = r.json()["results"]
    assert all(p["rating"] >= 4.8 for p in results)
    assert len(results) >= 1


def test_filter_verified_only(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"verified_only": "true"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 9
    assert all(p["verified"] for p in results)


def test_filter_rate_bucket_low(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"rate_bucket": "low"})
    assert r.status_code == 200
    results = r.json()["results"]
    # SparkClean $45 and GreenLawn $55
    assert len(results) == 2, f"expected 2 low-rate providers, got {len(results)}"
    for p in results:
        assert p["hourly_rate"] < 60
        assert p["rate_bucket"] == "low"


def test_filter_min_jobs_200(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"min_jobs": 200})
    assert r.status_code == 200
    results = r.json()["results"]
    assert all(p["jobs_completed"] >= 200 for p in results)
    # SparkClean 412, Sarah Chen 320, Rapid Repairs 218, MP Electrical 210 = 4
    assert len(results) == 4, f"expected 4, got {len(results)}: {[p['business_name'] for p in results]}"


# ---------------- Sort ----------------
def test_sort_price_asc(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"sort": "price_asc"})
    assert r.status_code == 200
    results = r.json()["results"]
    rates = [p["hourly_rate"] for p in results]
    assert rates == sorted(rates)
    assert rates[0] == 45  # SparkClean


def test_sort_price_desc(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"sort": "price_desc"})
    assert r.status_code == 200
    rates = [p["hourly_rate"] for p in r.json()["results"]]
    assert rates == sorted(rates, reverse=True)


def test_sort_rating(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"sort": "rating"})
    assert r.status_code == 200
    ratings = [p["rating"] for p in r.json()["results"]]
    assert ratings == sorted(ratings, reverse=True)


def test_sort_reviews(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"sort": "reviews"})
    assert r.status_code == 200
    counts = [p["reviews_count"] for p in r.json()["results"]]
    assert counts == sorted(counts, reverse=True)


# ---------------- Full-text ----------------
def test_search_q_plumbing(customer_session):
    r = customer_session.get(f"{API}/providers/search", params={"q": "plumbing"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) >= 1
    assert any("Sarah Chen" in p["business_name"] for p in results)


# ---------------- Profile detail ----------------
def test_profile_detail(customer_session):
    r = customer_session.get(f"{API}/providers/search")
    provider_id = r.json()["results"][0]["user_id"]
    r = customer_session.get(f"{API}/providers/{provider_id}")
    assert r.status_code == 200
    p = r.json()
    for k in ["bio", "gallery", "past_jobs", "reviews", "rate_bucket"]:
        assert k in p, f"missing {k}"
    assert isinstance(p["gallery"], list) and len(p["gallery"]) == 4
    assert isinstance(p["reviews"], list) and len(p["reviews"]) == 3
    for rev in p["reviews"]:
        for k in ["author_name", "rating", "text", "created_at"]:
            assert k in rev


def test_profile_not_found(customer_session):
    r = customer_session.get(f"{API}/providers/does-not-exist-xyz")
    assert r.status_code == 404


# ---------------- Route ordering ----------------
def test_route_me_not_shadowed(provider_session):
    r = provider_session.get(f"{API}/providers/me")
    # provider role may or may not have profile seeded; accept 200 or 404 but not 500
    assert r.status_code in (200, 404), f"unexpected {r.status_code} {r.text[:200]}"


def test_route_nearby(customer_session):
    r = customer_session.get(f"{API}/providers/nearby")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_search_still_works(customer_session):
    r = customer_session.get(f"{API}/providers/search")
    assert r.status_code == 200


# ---------------- Regression: forum & taxonomy still work ----------------
def test_regression_taxonomy(customer_session):
    r = customer_session.get(f"{API}/services/residential-taxonomy")
    assert r.status_code == 200


def test_regression_cost_guide(customer_session):
    r = customer_session.get(f"{API}/cost-guide")
    assert r.status_code in (200, 404)  # depends on presence
