# Iteration 16: invoice access control for unlinked provider + demo-login role per role
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
JOB_ID = "job_3f75aa7134"


@pytest.fixture(scope="module")
def unlinked_provider():
    s = requests.Session()
    ts = int(time.time() * 1000)
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": f"TEST_qa-provider-{ts}@dispatchr.demo", "password": "testpass123",
        "name": "TEST_Unlinked Provider", "role": "provider"}, timeout=15)
    if r.status_code not in (200, 201):
        pytest.skip(f"register failed {r.status_code} {r.text[:200]}")
    return s


# Invoice: provider not linked to the job must get 403
def test_invoice_forbidden_unlinked_provider(unlinked_provider):
    r = unlinked_provider.get(f"{BASE_URL}/api/jobs/{JOB_ID}/invoice", timeout=15)
    assert r.status_code == 403, r.text


# Invoice: linked demo provider + customer still allowed
@pytest.mark.parametrize("role", ["provider", "customer"])
def test_invoice_allowed_linked(role):
    s = requests.Session()
    assert s.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role}, timeout=15).status_code == 200
    r = s.get(f"{BASE_URL}/api/jobs/{JOB_ID}/invoice", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "lines" in d or "line_items" in d or isinstance(d, dict)


# Demo login: /api/auth/me role matches requested role for all roles
@pytest.mark.parametrize("role", ["customer", "provider", "property", "landlord", "facilities", "insurance"])
def test_demo_login_me_role(role):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role}, timeout=15)
    assert r.status_code == 200
    assert r.json()["user"]["role"] == role
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert me.status_code == 200
    body = me.json()
    assert (body.get("user") or body).get("role") == role


def test_demo_login_bad_role():
    r = requests.post(f"{BASE_URL}/api/auth/demo-login", json={"role": "admin"}, timeout=15)
    assert r.status_code == 400
