"""Tests for new forum behaviors: unique-viewer tracking + nested replies."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://next-gen-app-39.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
TS = int(time.time())


def _register(role: str, suffix: str):
    r = requests.post(f"{API}/auth/register", json={
        "email": f"forum2-{role}-{TS}-{suffix}@dispatchr.demo",
        "password": "testpass123",
        "name": f"QA {role.title()} {suffix}",
        "role": role,
        "phone": "0210000000",
        "city": "Auckland",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, r.json()["user"]


@pytest.fixture(scope="module")
def author():
    return _register("customer", "author")


@pytest.fixture(scope="module")
def viewer_a():
    return _register("customer", "viewA")


@pytest.fixture(scope="module")
def viewer_b():
    return _register("customer", "viewB")


@pytest.fixture(scope="module")
def created_post(author):
    hdr, _ = author
    r = requests.post(f"{API}/forum/posts", headers=hdr, json={
        "title": "TEST_ unique viewer + nested reply post",
        "body": "Body of test post for uniqueness / nesting behaviour.",
        "category": "renovations",
        "tags": ["qa"],
    })
    assert r.status_code == 200, r.text
    pid = r.json()["post_id"]
    yield pid
    requests.delete(f"{API}/forum/posts/{pid}", headers=hdr)


# ---------- Unique-viewer tracking ----------
def test_author_view_does_not_increment(author, created_post):
    hdr, _ = author
    r1 = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr)
    assert r1.status_code == 200
    v1 = r1.json()["post"].get("views", 0)
    r2 = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr)
    v2 = r2.json()["post"].get("views", 0)
    assert v1 == v2, f"author view incremented views {v1}->{v2}"


def test_new_viewer_increments_once(author, viewer_a, created_post):
    hdr_a, _ = viewer_a
    # baseline via author (does not increment)
    hdr_author, _ = author
    baseline = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr_author).json()["post"]["views"]

    r1 = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr_a)
    v1 = r1.json()["post"]["views"]
    assert v1 == baseline + 1, f"expected +1 got {baseline}->{v1}"

    # Second hit by same user should NOT increment
    r2 = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr_a)
    v2 = r2.json()["post"]["views"]
    assert v2 == v1, f"duplicate view incremented {v1}->{v2}"


def test_different_viewer_increments_again(author, viewer_a, viewer_b, created_post):
    hdr_author, _ = author
    baseline = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr_author).json()["post"]["views"]
    hdr_b, _ = viewer_b
    r = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr_b)
    assert r.json()["post"]["views"] == baseline + 1


def test_viewers_field_not_leaked(author, created_post):
    hdr, _ = author
    r = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr)
    assert "viewers" not in r.json()["post"], "viewers field must not be exposed to clients"


# ---------- Nested replies ----------
def test_nested_reply_creation_and_retrieval(author, viewer_a, created_post):
    hdr_author, _ = author
    hdr_a, _ = viewer_a

    # Top-level reply
    r_parent = requests.post(f"{API}/forum/posts/{created_post}/replies", headers=hdr_a, json={
        "body": "Top-level reply for nesting test",
    })
    assert r_parent.status_code == 200, r_parent.text
    parent_id = r_parent.json()["reply_id"]
    assert r_parent.json().get("parent_reply_id") in (None, "")

    # Child reply
    r_child = requests.post(f"{API}/forum/posts/{created_post}/replies", headers=hdr_author, json={
        "body": "Child reply referencing parent",
        "parent_reply_id": parent_id,
    })
    assert r_child.status_code == 200, r_child.text
    child_id = r_child.json()["reply_id"]
    assert r_child.json()["parent_reply_id"] == parent_id

    # GET returns both in flat replies[]
    detail = requests.get(f"{API}/forum/posts/{created_post}", headers=hdr_a).json()
    ids = {r["reply_id"]: r for r in detail["replies"]}
    assert parent_id in ids and child_id in ids
    assert ids[child_id]["parent_reply_id"] == parent_id
    assert ids[parent_id].get("parent_reply_id") in (None, "")
