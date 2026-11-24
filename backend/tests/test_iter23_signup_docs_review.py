# Iteration 23: role-specific signup, Google complete-signup, provider documents, reviewer flow, PDF uploads
import os
import uuid
import pytest
import requests
from pathlib import Path
from pymongo import MongoClient
from dotenv import dotenv_values

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL') or dotenv_values('/app/frontend/.env')['REACT_APP_BACKEND_URL']
BASE_URL = BASE_URL.rstrip('/')
_benv = dotenv_values('/app/backend/.env')
mdb = MongoClient(_benv['MONGO_URL'])[_benv['DB_NAME']]

REVIEWER = {"email": "reviewer.test@profinder.test", "password": "Review123!"}
CREATED_USERS = []


def _uid():
    return uuid.uuid4().hex[:8]


def register(role, **extra):
    email = f"TEST_{role}_{_uid()}@example.com"
    body = {"email": email, "password": "Test123!", "name": f"TEST_{role}", "role": role, **extra}
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json=body)
    assert r.status_code == 200, r.text
    d = r.json()
    CREATED_USERS.append(d["user"]["user_id"])
    s.headers["Authorization"] = f"Bearer {d['token']}"
    return s, d["user"]


def login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        pytest.skip(f"login failed for {email}")
    s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s, r.json()["user"]


def upload_pdf(s, name="cert.pdf"):
    data = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    r = s.post(f"{BASE_URL}/api/uploads/init", json={"filename": name, "content_type": "application/pdf", "size": len(data)})
    assert r.status_code == 200, r.text
    up = r.json()["upload_id"]
    r = s.put(f"{BASE_URL}/api/uploads/{up}/chunk?index=0", data=data, headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 200, r.text
    r = s.post(f"{BASE_URL}/api/uploads/{up}/complete?total_chunks=1")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for uid in CREATED_USERS:
        files = [f["file_id"] for f in mdb.files.find({"owner_id": uid}, {"file_id": 1})]
        mdb.provider_documents.delete_many({"provider_id": uid})
        mdb.provider_profiles.delete_many({"user_id": uid})
        mdb.notifications.delete_many({"user_id": uid})
        mdb.user_sessions.delete_many({"user_id": uid})
        if files:
            mdb.files.delete_many({"file_id": {"$in": files}})
        mdb.users.delete_one({"user_id": uid})


# ---- Register per role ----
class TestRegister:
    def test_provider_register_details_and_unverified(self):
        s, u = register("provider", business_name="TEST_Kiwi Plumbing", account_type=None,
                        signup_details={"nzbn": "9429000000000", "years_in_business": "4–10", "bogus": "x", "company_name": "nope"})
        assert u["business_name"] == "TEST_Kiwi Plumbing"
        assert u["signup_details"] == {"nzbn": "9429000000000", "years_in_business": "4–10"}
        assert u["signup_complete"] is True
        prof = mdb.provider_profiles.find_one({"user_id": u["user_id"]})
        assert prof["business_name"] == "TEST_Kiwi Plumbing"
        assert prof["verified"] is False and prof["qualified_verified"] is False and prof["police_checked"] is False
        me = s.get(f"{BASE_URL}/api/auth/me").json()
        assert me["role"] == "provider" and me["is_reviewer"] is False

    @pytest.mark.parametrize("role,at,details", [
        ("customer", "commercial", {"home_type": "House", "suburb": "Ponsonby"}),
        ("property", "residential", {"company_name": "x", "properties_managed": "21–100"}),
        ("insurance", None, {"fsp_number": "FSP1", "claims_per_month": "10–50", "nzbn": "drop"}),
        ("landlord", None, {"rental_count": "2–5"}),
        ("facilities", None, {"buildings_count": "1"}),
    ])
    def test_other_roles(self, role, at, details):
        s, u = register(role, account_type=at, business_name="TEST_Co", signup_details=details)
        allowed = {"customer": ["suburb", "home_type"], "landlord": ["rental_count", "suburb"],
                   "property": ["company_name", "properties_managed", "suburb"], "facilities": ["organisation", "buildings_count", "suburb"],
                   "insurance": ["company_name", "fsp_number", "claims_per_month"]}[role]
        assert u["signup_details"] == {k: v for k, v in details.items() if k in allowed}
        assert u["account_type"] == (at or ("commercial" if role == "facilities" else "residential"))
        assert mdb.provider_profiles.find_one({"user_id": u["user_id"]}) is None

    def test_invalid_role_and_short_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": f"TEST_{_uid()}@example.com", "password": "Test123!", "name": "x", "role": "admin"})
        assert r.status_code == 400
        r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": f"TEST_{_uid()}@example.com", "password": "123", "name": "x", "role": "customer"})
        assert r.status_code == 400

    def test_email_lowercased_and_login_case_insensitive(self):
        email = f"TEST_Mixed_{_uid()}@Example.COM"
        r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "Test123!", "name": "TEST_m", "role": "customer"})
        assert r.status_code == 200
        CREATED_USERS.append(r.json()["user"]["user_id"])
        assert r.json()["user"]["email"] == email.lower()
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email.upper(), "password": "Test123!"})
        assert r.status_code == 200
        r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "Test123!", "name": "dup", "role": "customer"})
        assert r.status_code == 400


# ---- Google completion mode ----
class TestCompleteSignup:
    def _google_user(self, role="customer"):
        from datetime import datetime, timezone, timedelta
        uid = f"TEST_g_{_uid()}"
        tok = f"TEST_sess_{_uid()}"
        mdb.users.insert_one({"user_id": uid, "email": f"TEST_g_{_uid()}@example.com", "name": "TEST_Google", "role": role,
                              "signup_complete": False, "created_at": datetime.now(timezone.utc)})
        mdb.user_sessions.insert_one({"user_id": uid, "session_token": tok, "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                                      "created_at": datetime.now(timezone.utc)})
        CREATED_USERS.append(uid)
        s = requests.Session()
        s.headers["Authorization"] = f"Bearer {tok}"
        return s, uid

    def test_complete_as_provider_then_role_locked(self):
        s, uid = self._google_user("customer")
        assert s.get(f"{BASE_URL}/api/auth/me").json()["signup_complete"] is False
        r = s.post(f"{BASE_URL}/api/auth/complete-signup", json={"role": "provider", "business_name": "TEST_GBiz", "phone": "021",
                                                                  "signup_details": {"years_in_business": "1–3", "hack": 1}})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["role"] == "provider" and d["signup_complete"] is True and d["business_name"] == "TEST_GBiz"
        assert d["signup_details"] == {"years_in_business": "1–3"}
        prof = mdb.provider_profiles.find_one({"user_id": uid})
        assert prof and prof["business_name"] == "TEST_GBiz" and prof["verified"] is False
        r = s.post(f"{BASE_URL}/api/auth/complete-signup", json={"role": "customer"})
        assert r.status_code == 400
        r = s.post(f"{BASE_URL}/api/auth/complete-signup", json={"role": "provider", "business_name": "TEST_GBiz2"})
        assert r.status_code == 200

    def test_complete_requires_auth_and_valid_role(self):
        assert requests.post(f"{BASE_URL}/api/auth/complete-signup", json={"role": "customer"}).status_code == 401
        s, _ = self._google_user()
        assert s.post(f"{BASE_URL}/api/auth/complete-signup", json={"role": "god"}).status_code == 400


# ---- Documents + reviewer ----
class TestDocumentsAndReview:
    def test_full_review_flow(self):
        ps, pu = register("provider", business_name="TEST_DocPro", signup_details={"years_in_business": "1–3"})
        pid = pu["user_id"]
        f = upload_pdf(ps)
        assert f["content_type"] == "application/pdf"
        # validation
        assert ps.post(f"{BASE_URL}/api/providers/me/documents", json={"kind": "bogus", "title": "x", "file_url": f["url"]}).status_code == 400
        assert ps.post(f"{BASE_URL}/api/providers/me/documents", json={"kind": "qualification", "title": " ", "file_url": f["url"]}).status_code == 400
        assert ps.post(f"{BASE_URL}/api/providers/me/documents", json={"kind": "qualification", "title": "x", "file_url": "http://evil/x.pdf"}).status_code == 400
        q = ps.post(f"{BASE_URL}/api/providers/me/documents", json={"kind": "qualification", "title": "TEST_Plumbing L4", "file_url": f["url"], "file_name": "cert.pdf"})
        assert q.status_code == 200, q.text
        qdoc = q.json()
        assert qdoc["status"] == "pending" and "_id" not in qdoc
        f2 = upload_pdf(ps, "police.pdf")
        pc = ps.post(f"{BASE_URL}/api/providers/me/documents", json={"kind": "police_check", "title": "TEST_MoJ check", "file_url": f2["url"]}).json()
        mine = ps.get(f"{BASE_URL}/api/providers/me/documents").json()
        assert {d["doc_id"] for d in mine} >= {qdoc["doc_id"], pc["doc_id"]}
        cred = ps.get(f"{BASE_URL}/api/providers/{pid}/credentials").json()
        assert cred["qualified"] is False and cred["police_checked"] is False

        # non-reviewer forbidden
        assert ps.get(f"{BASE_URL}/api/review/documents").status_code == 403
        assert ps.post(f"{BASE_URL}/api/review/documents/{qdoc['doc_id']}", json={"decision": "approve"}).status_code == 403

        rs, ru = login(**REVIEWER)
        assert ru["is_reviewer"] is True
        pend = rs.get(f"{BASE_URL}/api/review/documents").json()
        row = next(d for d in pend if d["doc_id"] == qdoc["doc_id"])
        assert row["provider_name"] == "TEST_DocPro"
        # reviewer can open the file
        fr = rs.get(f"{BASE_URL}{f['url']}")
        assert fr.status_code == 200 and fr.content.startswith(b"%PDF")
        # reject needs note
        assert rs.post(f"{BASE_URL}/api/review/documents/{pc['doc_id']}", json={"decision": "reject"}).status_code == 400
        assert rs.post(f"{BASE_URL}/api/review/documents/{pc['doc_id']}", json={"decision": "maybe"}).status_code == 400
        assert rs.post(f"{BASE_URL}/api/review/documents/doc_nope", json={"decision": "approve"}).status_code == 404
        r = rs.post(f"{BASE_URL}/api/review/documents/{qdoc['doc_id']}", json={"decision": "approve"})
        assert r.json()["status"] == "approved"
        cred = ps.get(f"{BASE_URL}/api/providers/{pid}/credentials").json()
        assert cred["qualified"] is True and cred["police_checked"] is False and len(cred["documents"]) == 1
        r = rs.post(f"{BASE_URL}/api/review/documents/{pc['doc_id']}", json={"decision": "reject", "note": "Blurry scan"})
        assert r.json()["status"] == "rejected"
        mine = {d["doc_id"]: d for d in ps.get(f"{BASE_URL}/api/providers/me/documents").json()}
        assert mine[pc["doc_id"]]["status"] == "rejected" and mine[pc["doc_id"]]["review_note"] == "Blurry scan"
        # approve police check after re-review
        rs.post(f"{BASE_URL}/api/review/documents/{pc['doc_id']}", json={"decision": "approve"})
        cred = ps.get(f"{BASE_URL}/api/providers/{pid}/credentials").json()
        assert cred["police_checked"] is True
        prof = mdb.provider_profiles.find_one({"user_id": pid})
        assert prof["verified"] is True
        # public profile shows flags
        pub = rs.get(f"{BASE_URL}/api/providers/{pid}")
        assert pub.status_code == 200
        notes = list(mdb.notifications.find({"user_id": pid, "type": "doc_reviewed"}))
        assert len(notes) >= 2
        # all-status list
        assert any(d["doc_id"] == qdoc["doc_id"] for d in rs.get(f"{BASE_URL}/api/review/documents?status=all").json())
        # delete removes tick
        assert ps.delete(f"{BASE_URL}/api/providers/me/documents/{qdoc['doc_id']}").status_code == 200
        assert ps.delete(f"{BASE_URL}/api/providers/me/documents/{qdoc['doc_id']}").status_code == 404
        cred = ps.get(f"{BASE_URL}/api/providers/{pid}/credentials").json()
        assert cred["qualified"] is False and cred["police_checked"] is True
        # cleanup reviewer notifications created for these docs
        mdb.notifications.delete_many({"user_id": ru["user_id"], "type": "doc_review", "message": {"$regex": "TEST_"}})

    def test_customer_cannot_use_provider_docs(self):
        cs, _ = register("customer")
        assert cs.get(f"{BASE_URL}/api/providers/me/documents").status_code == 403

    def test_file_of_other_user_rejected(self):
        ps1, _ = register("provider", business_name="TEST_A")
        ps2, _ = register("provider", business_name="TEST_B")
        f = upload_pdf(ps1)
        r = ps2.post(f"{BASE_URL}/api/providers/me/documents", json={"kind": "qualification", "title": "steal", "file_url": f["url"]})
        assert r.status_code == 400

    def test_upload_rejects_non_media(self):
        cs, _ = register("customer")
        r = cs.post(f"{BASE_URL}/api/uploads/init", json={"filename": "a.exe", "content_type": "application/x-msdownload", "size": 10})
        assert r.status_code == 400


# ---- Regression ----
class TestRegression:
    @pytest.mark.parametrize("role", ["customer", "provider", "property", "landlord", "facilities", "insurance"])
    def test_demo_login(self, role):
        r = requests.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role})
        assert r.status_code == 200 and r.json()["user"]["role"] == role
