# Iteration 23 security probes around provider verification (expected to FAIL until fixed)
import pytest
import requests
from test_iter23_signup_docs_review import BASE_URL, mdb, register, upload_pdf, cleanup  # noqa: F401


def test_role_switch_does_not_grant_verified():
    s, u = register("customer")
    r = s.patch(f"{BASE_URL}/api/auth/role", json={"role": "provider"})
    assert r.status_code == 200
    prof = mdb.provider_profiles.find_one({"user_id": u["user_id"]})
    assert prof.get("verified") is not True, "PATCH /auth/role auto-creates provider profile with verified=True/insured=True"


def test_other_user_cannot_read_police_check_file():
    ps, _ = register("provider", business_name="TEST_Priv")
    f = upload_pdf(ps, "police.pdf")
    ps.post(f"{BASE_URL}/api/providers/me/documents", json={"kind": "police_check", "title": "TEST_pc", "file_url": f["url"]})
    cs, _ = register("customer")
    r = cs.get(f"{BASE_URL}{f['url']}")
    assert r.status_code in (403, 404), "any logged-in user can download a provider's police-check document"
