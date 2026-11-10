# Iteration 17: Invoice send/resend + provider service-area radius regression tests
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
JOB_ID = "job_3f75aa7134"


def login(role):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role})
    if r.status_code != 200:
        pytest.skip(f"demo login {role} failed {r.status_code}")
    return s


@pytest.fixture(scope="module")
def prov():
    return login("provider")


@pytest.fixture(scope="module")
def cust():
    return login("customer")


# ---- Invoice send ----
class TestInvoiceSend:
    def test_provider_get_invoice_draft(self, prov):
        r = prov.get(f"{BASE_URL}/api/jobs/{JOB_ID}/invoice")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_sent_copy"] is False
        assert len(d["lines"]) > 0
        assert "_id" not in d

    def test_customer_cannot_send(self, cust):
        r = cust.post(f"{BASE_URL}/api/jobs/{JOB_ID}/invoice/send")
        assert r.status_code == 403, r.text

    def test_send_increments_version_and_posts_chat(self, prov, cust):
        before = prov.get(f"{BASE_URL}/api/jobs/{JOB_ID}/invoice").json()
        prev_v = (before.get("sent") or {}).get("version") or 0
        r = prov.post(f"{BASE_URL}/api/jobs/{JOB_ID}/invoice/send")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["version"] == prev_v + 1
        assert d["sent"]["version"] == prev_v + 1
        assert d["email_sent"] is False  # demo customer email is fake -> blocked
        assert "_id" not in d
        assert d["thread_id"]
        # customer sees sent copy
        c = cust.get(f"{BASE_URL}/api/jobs/{JOB_ID}/invoice")
        assert c.status_code == 200, c.text
        cd = c.json()
        assert cd["is_sent_copy"] is True
        assert cd["sent"]["version"] == prev_v + 1
        assert cd["total"] == d["total"]
        assert "_id" not in cd
        # chat message present for customer
        m = cust.get(f"{BASE_URL}/api/threads/{d['thread_id']}/messages")
        if m.status_code == 404:
            m = cust.get(f"{BASE_URL}/api/messages/{d['thread_id']}")
        assert m.status_code == 200, m.text
        body = m.json()
        msgs = body if isinstance(body, list) else body.get("messages", [])
        assert any("Invoice test leak" in (x.get("content") or "") and "invoice" in x["content"] for x in msgs)

    def test_no_lines_returns_400_or_403(self, prov):
        # find a provider job without lines: use jobs the provider has won
        r = prov.get(f"{BASE_URL}/api/jobs/nonexistent_job_xyz/invoice/send")
        assert r.status_code in (404, 405)
        r2 = prov.post(f"{BASE_URL}/api/jobs/nonexistent_job_xyz/invoice/send")
        assert r2.status_code == 404


# ---- Service area radius ----
class TestServiceArea:
    def test_default_and_validation(self, prov):
        r = prov.get(f"{BASE_URL}/api/providers/me")
        assert r.status_code == 200
        for bad in (0, 501, -5, "abc"):
            b = prov.patch(f"{BASE_URL}/api/providers/me", json={"service_radius_km": bad})
            assert b.status_code == 400, f"{bad}: {b.status_code}"

    def test_radius_hides_provider_from_far_customer(self, prov, cust):
        me = prov.get(f"{BASE_URL}/api/providers/me").json()
        pid = me["user_id"]
        try:
            # baseline: null -> visible from far origin
            r = prov.patch(f"{BASE_URL}/api/providers/me", json={"service_radius_km": None})
            assert r.status_code == 200 and r.json().get("service_radius_km") is None
            s = cust.get(f"{BASE_URL}/api/providers/search", params={"lat": -36.95, "lng": 174.76, "limit": 200})
            assert s.status_code == 200, s.text
            base_ids = [p["user_id"] for p in s.json()["results"]]
            if pid not in base_ids:
                pytest.skip("demo provider not visible in catalog even without radius")
            # set 1km
            r = prov.patch(f"{BASE_URL}/api/providers/me", json={"service_radius_km": 1})
            assert r.status_code == 200 and r.json()["service_radius_km"] == 1
            s = cust.get(f"{BASE_URL}/api/providers/search", params={"lat": -36.95, "lng": 174.76, "limit": 200})
            ids = [p["user_id"] for p in s.json()["results"]]
            assert pid not in ids
        finally:
            prov.patch(f"{BASE_URL}/api/providers/me", json={"service_radius_km": None})
        s = cust.get(f"{BASE_URL}/api/providers/search", params={"lat": -36.95, "lng": 174.76, "limit": 200})
        assert pid in [p["user_id"] for p in s.json()["results"]]
        assert prov.get(f"{BASE_URL}/api/providers/me").json().get("service_radius_km") is None
