"""Backend tests for Community Forum feature (roles: provider vs customer)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://next-gen-app-39.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

TS = int(time.time())


def _register(role: str, suffix: str):
    email = f"forumqa-{role}-{TS}-{suffix}@dispatchr.demo"
    r = requests.post(f"{API}/auth/register", json={
        "email": email,
        "password": "testpass123",
        "name": f"QA {role.title()} {suffix}",
        "role": role,
        "phone": "0210000000",
        "city": "Auckland",
    })
    assert r.status_code == 200, f"register {role}: {r.status_code} {r.text}"
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}, r.json()["user"]


@pytest.fixture(scope="module")
def provider():
    hdr, user = _register("provider", "a")
    return hdr, user


@pytest.fixture(scope="module")
def customer():
    hdr, user = _register("customer", "b")
    return hdr, user


# --------- Categories ---------
def test_provider_categories(provider):
    hdr, _ = provider
    r = requests.get(f"{API}/forum/categories", headers=hdr)
    assert r.status_code == 200
    data = r.json()
    assert data["audience"] == "provider"
    ids = [c["id"] for c in data["categories"]]
    expected = {"pricing", "reno-projects", "maintenance-ops", "compliance", "suppliers",
                "tools-materials", "business", "market-trends", "smoko-room"}
    assert set(ids) == expected, f"got {ids}"
    assert len(data["categories"]) == 9


def test_customer_categories(customer):
    hdr, _ = customer
    r = requests.get(f"{API}/forum/categories", headers=hdr)
    assert r.status_code == 200
    data = r.json()
    assert data["audience"] == "customer"
    ids = [c["id"] for c in data["categories"]]
    expected = {"maintenance", "renovations", "diy-vs-pro", "reviews", "cost-questions",
                "smart-home", "landlord-corner", "disputes"}
    assert set(ids) == expected
    assert len(data["categories"]) == 8


# --------- Seeded posts visibility & isolation ---------
def test_provider_sees_seeded_posts(provider):
    hdr, _ = provider
    r = requests.get(f"{API}/forum/posts", headers=hdr)
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) >= 9
    assert all(p["audience"] == "provider" for p in posts)


def test_customer_sees_different_posts(provider, customer):
    hdr_c, _ = customer
    hdr_p, _ = provider
    rc = requests.get(f"{API}/forum/posts", headers=hdr_c)
    rp = requests.get(f"{API}/forum/posts", headers=hdr_p)
    assert rc.status_code == 200 and rp.status_code == 200
    cust_posts = rc.json()
    prov_posts = rp.json()
    assert len(cust_posts) >= 8
    assert all(p["audience"] == "customer" for p in cust_posts)
    cust_ids = {p["post_id"] for p in cust_posts}
    prov_ids = {p["post_id"] for p in prov_posts}
    assert cust_ids.isdisjoint(prov_ids)


# --------- Sort ---------
def test_sort_new(customer):
    hdr, _ = customer
    r = requests.get(f"{API}/forum/posts?sort=new", headers=hdr)
    assert r.status_code == 200
    posts = r.json()
    times = [p["created_at"] for p in posts]
    assert times == sorted(times, reverse=True)


def test_sort_top(customer):
    hdr, _ = customer
    r = requests.get(f"{API}/forum/posts?sort=top", headers=hdr)
    assert r.status_code == 200
    posts = r.json()
    ups = [p["upvotes"] for p in posts]
    assert ups == sorted(ups, reverse=True)


# --------- Search ---------
def test_search_keyword(customer):
    hdr, _ = customer
    r = requests.get(f"{API}/forum/posts?q=bathroom", headers=hdr)
    assert r.status_code == 200
    posts = r.json()
    for p in posts:
        blob = (p["title"] + " " + p["body"]).lower()
        assert "bathroom" in blob


# --------- Category filter ---------
def test_category_filter(customer):
    hdr, _ = customer
    r = requests.get(f"{API}/forum/posts?category=renovations", headers=hdr)
    assert r.status_code == 200
    for p in r.json():
        assert p["category"] == "renovations"


# --------- Post detail + replies ---------
def test_post_detail_and_replies(customer):
    hdr, _ = customer
    posts = requests.get(f"{API}/forum/posts", headers=hdr).json()
    pid = posts[0]["post_id"]
    r = requests.get(f"{API}/forum/posts/{pid}", headers=hdr)
    assert r.status_code == 200
    data = r.json()
    assert data["post"]["post_id"] == pid
    assert "replies" in data
    assert "title" in data["post"] and "body" in data["post"]


# --------- Cross-audience isolation ---------
def test_customer_cannot_access_provider_post(provider, customer):
    hdr_p, _ = provider
    hdr_c, _ = customer
    prov_posts = requests.get(f"{API}/forum/posts", headers=hdr_p).json()
    pid = prov_posts[0]["post_id"]
    r = requests.get(f"{API}/forum/posts/{pid}", headers=hdr_c)
    assert r.status_code == 403


# --------- Create post + vote + reply + delete ---------
def test_full_post_lifecycle(customer):
    hdr, user = customer
    # Create
    r = requests.post(f"{API}/forum/posts", headers=hdr, json={
        "title": "TEST_ QA new bathroom reno post",
        "body": "Testing full lifecycle of a customer post. This is a body over 10 chars.",
        "category": "renovations",
        "tags": ["qa", "test"],
    })
    assert r.status_code == 200, r.text
    post = r.json()
    pid = post["post_id"]
    assert post["upvotes"] == 1

    # Appears at top of new-sorted feed
    feed = requests.get(f"{API}/forum/posts?sort=new", headers=hdr).json()
    assert feed[0]["post_id"] == pid

    # Vote: toggle to 0 then back to 1
    r = requests.post(f"{API}/forum/posts/{pid}/vote", headers=hdr, json={"value": 0})
    assert r.status_code == 200 and r.json()["upvotes"] == 0
    r = requests.post(f"{API}/forum/posts/{pid}/vote", headers=hdr, json={"value": 1})
    assert r.status_code == 200 and r.json()["upvotes"] == 1
    r = requests.post(f"{API}/forum/posts/{pid}/vote", headers=hdr, json={"value": -1})
    assert r.status_code == 200 and r.json()["downvotes"] == 1 and r.json()["upvotes"] == 0

    # Reply
    r = requests.post(f"{API}/forum/posts/{pid}/replies", headers=hdr, json={"body": "great question, here's my take"})
    assert r.status_code == 200
    rid = r.json()["reply_id"]

    # replies_count incremented
    detail = requests.get(f"{API}/forum/posts/{pid}", headers=hdr).json()
    assert detail["post"]["replies_count"] == 1
    assert any(rp["reply_id"] == rid for rp in detail["replies"])

    # Vote reply
    r = requests.post(f"{API}/forum/replies/{rid}/vote", headers=hdr, json={"value": -1})
    assert r.status_code == 200

    # Delete post
    r = requests.delete(f"{API}/forum/posts/{pid}", headers=hdr)
    assert r.status_code == 200
    r = requests.get(f"{API}/forum/posts/{pid}", headers=hdr)
    assert r.status_code == 404


def test_create_post_wrong_category_rejected(customer):
    hdr, _ = customer
    r = requests.post(f"{API}/forum/posts", headers=hdr, json={
        "title": "TEST_ using provider cat",
        "body": "Should be rejected because pricing is provider-only",
        "category": "pricing",
        "tags": [],
    })
    assert r.status_code == 400


def test_create_post_validation(customer):
    hdr, _ = customer
    r = requests.post(f"{API}/forum/posts", headers=hdr, json={
        "title": "hi", "body": "12345678901", "category": "renovations", "tags": []
    })
    assert r.status_code == 400
    r = requests.post(f"{API}/forum/posts", headers=hdr, json={
        "title": "long enough title", "body": "short", "category": "renovations", "tags": []
    })
    assert r.status_code == 400


def test_delete_others_post_forbidden(provider, customer):
    hdr_p, _ = provider
    # provider creates a post
    r = requests.post(f"{API}/forum/posts", headers=hdr_p, json={
        "title": "TEST_ provider only post for deletion",
        "body": "This should not be deletable by another provider",
        "category": "pricing", "tags": []
    })
    assert r.status_code == 200
    pid = r.json()["post_id"]
    # register another provider
    hdr_p2, _ = _register("provider", "c")
    r = requests.delete(f"{API}/forum/posts/{pid}", headers=hdr_p2)
    assert r.status_code == 403
    # cleanup
    requests.delete(f"{API}/forum/posts/{pid}", headers=hdr_p)


def test_forum_stats(customer):
    hdr, _ = customer
    r = requests.get(f"{API}/forum/stats", headers=hdr)
    assert r.status_code == 200
    data = r.json()
    assert data["audience"] == "customer"
    assert data["posts"] >= 8
    assert "replies" in data and "members" in data


def test_unauthenticated_forum_blocked():
    r = requests.get(f"{API}/forum/categories")
    assert r.status_code == 401
