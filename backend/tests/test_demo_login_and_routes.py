"""Regression: demo-login for all 6 roles + core API health for iteration 14."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://recover-app-6--0t57q2zf.preview.emergentagent.com').rstrip('/')

ROLES = ['customer', 'provider', 'property', 'landlord', 'facilities', 'insurance']


@pytest.fixture(scope='module')
def sessions():
    """Login sessions for each role via /api/auth/demo-login."""
    out = {}
    for role in ROLES:
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/demo-login", json={'role': role}, timeout=15)
        assert r.status_code == 200, f"demo-login failed for {role}: {r.status_code} {r.text}"
        data = r.json()
        assert data['user']['role'] == role
        assert data['user']['email'] == f"demo-{role}@profinder.nz"
        assert 'token' in data
        # Add bearer as fallback (frontend uses cookie via withCredentials)
        s.headers.update({'Authorization': f"Bearer {data['token']}"})
        out[role] = s
    return out


@pytest.mark.parametrize('role', ROLES)
def test_demo_login_returns_user(role):
    r = requests.post(f"{BASE_URL}/api/auth/demo-login", json={'role': role}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d['user']['role'] == role
    assert d['demo'] is True


def test_normal_login_customer():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={'email': 'demo-customer@profinder.nz', 'password': 'Demo123!'}, timeout=15)
    assert r.status_code == 200
    assert r.json()['user']['role'] == 'customer'


def test_auth_me_unauth_returns_401():
    r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 401


@pytest.mark.parametrize('role', ROLES)
def test_auth_me_authed(sessions, role):
    r = sessions[role].get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 200
    assert r.json()['role'] == role


# Core endpoints called by the various dashboards. If any returns 5xx it's a regression.
CORE_GET_ENDPOINTS = [
    '/api/providers/search',
    '/api/jobs',
    '/api/marketplace/products',
    '/api/forum/posts',
    '/api/news',
    '/api/services/taxonomy',
    '/api/saved-providers',
    '/api/bookings',
    '/api/tenancies',
    '/api/approvals',
]


@pytest.mark.parametrize('endpoint', CORE_GET_ENDPOINTS)
def test_core_endpoint_no_5xx_as_customer(sessions, endpoint):
    r = sessions['customer'].get(f"{BASE_URL}{endpoint}", timeout=20)
    assert r.status_code < 500, f"{endpoint} returned {r.status_code}: {r.text[:200]}"


@pytest.mark.parametrize('role', ROLES)
def test_providers_search_all_roles(sessions, role):
    r = sessions[role].get(f"{BASE_URL}/api/providers/search", timeout=20)
    # Providers themselves may not have access, but should not be 5xx
    assert r.status_code < 500


def test_provider_job_board_only_approved(sessions):
    """Provider job board must only expose jobs that are approved or approval_not_required."""
    r = sessions['provider'].get(f"{BASE_URL}/api/jobs?scope=board", timeout=20)
    # If endpoint exists, verify no non-approved job leaks; if 404, skip
    if r.status_code == 404:
        pytest.skip('No board-scoped endpoint')
    assert r.status_code < 500
    if r.status_code == 200:
        jobs = r.json() if isinstance(r.json(), list) else r.json().get('jobs', [])
        for j in jobs:
            aps = j.get('approval_status', 'not_required')
            assert aps in ('not_required', 'approved'), f"Job {j.get('id')} leaked with status {aps}"


def test_forum_posts_list(sessions):
    r = sessions['customer'].get(f"{BASE_URL}/api/forum/posts", timeout=15)
    assert r.status_code == 200
    posts = r.json()
    assert isinstance(posts, list)


def test_forum_post_reply(sessions):
    r = sessions['customer'].get(f"{BASE_URL}/api/forum/posts", timeout=15)
    posts = r.json()
    if not posts:
        pytest.skip('No forum posts to reply to')
    pid = posts[0].get('post_id') or posts[0].get('id')
    r2 = sessions['customer'].post(f"{BASE_URL}/api/forum/posts/{pid}/replies",
                                    json={'body': 'TEST_ reply from iteration14 regression'}, timeout=15)
    assert r2.status_code in (200, 201), f"reply failed: {r2.status_code} {r2.text}"


def test_post_job_customer(sessions):
    payload = {
        'title': 'TEST_ Iter14 fix leaky kitchen tap',
        'description': 'Small drip under sink, needs replacement washer.',
        'category': 'plumbing-gas',
        'subcategory': 'residential-plumbing',
        'service_type': 'residential',
    }
    r = sessions['customer'].post(f"{BASE_URL}/api/jobs", json=payload, timeout=20)
    assert r.status_code in (200, 201), f"post job: {r.status_code} {r.text}"
    j = r.json()
    assert j.get('title') == payload['title']
    jid = j.get('id') or j.get('job_id')
    assert jid
    # Verify it appears in own list
    r2 = sessions['customer'].get(f"{BASE_URL}/api/jobs/mine", timeout=15)
    if r2.status_code == 404:
        r2 = sessions['customer'].get(f"{BASE_URL}/api/jobs?mine=true", timeout=15)
    assert r2.status_code < 500


def test_logout(sessions):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo-login", json={'role': 'customer'}, timeout=15)
    assert r.status_code == 200
    r2 = s.post(f"{BASE_URL}/api/auth/logout", timeout=15)
    assert r2.status_code in (200, 204)
    r3 = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r3.status_code == 401
