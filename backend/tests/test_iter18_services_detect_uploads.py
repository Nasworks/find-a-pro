# Iteration 18: new taxonomy categories, service auto-detect, provider category aliases, chunked media uploads
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


def _login(role):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo-login", json={"role": role})
    if r.status_code != 200:
        pytest.skip(f"demo login failed for {role}")
    return s


@pytest.fixture(scope="module")
def customer():
    return _login("customer")


@pytest.fixture(scope="module")
def provider():
    return _login("provider")


# ---- Taxonomy ----
class TestTaxonomy:
    def test_residential_new_categories(self):
        r = requests.get(f"{BASE_URL}/api/services/taxonomy/residential")
        assert r.status_code == 200
        data = r.json()
        cats = data if isinstance(data, list) else data.get("categories", data)
        assert len(cats) == 25
        by_id = {c["id"]: c for c in cats}
        g = by_id["gardening-lawn"]
        assert g["name"] == "Gardening & Lawn" and len(g["subcategories"]) == 13
        names = {s["name"] for s in g["subcategories"]}
        assert {"Lawn Mowing", "Hedge Trimming", "Tree Felling & Removal"} <= names
        assert len(by_id["landscaping"]["subcategories"]) == 11
        c = by_id["cleaning"]
        assert len(c["subcategories"]) == 16
        assert {"End of Tenancy Cleaning", "Water Blasting", "Carpet Cleaning"} <= {s["name"] for s in c["subcategories"]}

    def test_commercial_taxonomy_back(self):
        r = requests.get(f"{BASE_URL}/api/services/taxonomy/commercial")
        assert r.status_code == 200


# ---- Auto-detect ----
DETECT_CASES = [
    ("Leaking kitchen tap", "residential", "Plumbing & Gas", "Tap & Toilet Repairs"),
    ("need my lawns mowed", "residential", "Gardening & Lawn", "Lawn Mowing"),
    ("hedge overgrown", "residential", None, "Hedge Trimming"),
    ("bond clean when I move out", "residential", "Cleaning & Home Hygiene", None),
    ("moss on roof", "residential", None, "Roof Cleaning & Moss Treatment"),
]


class TestDetect:
    @pytest.mark.parametrize("text,st,cat,sub", DETECT_CASES)
    def test_detect(self, text, st, cat, sub):
        r = requests.get(f"{BASE_URL}/api/services/detect", params={"text": text, "service_type": st})
        assert r.status_code == 200
        d = r.json()
        m = d["match"]
        assert m is not None, f"no match for {text}"
        for k in ["category_id", "category_name", "subcategory_id", "subcategory_name"]:
            assert k in m
        assert isinstance(d["alternatives"], list)
        if cat:
            assert m["category_name"] == cat, f"{text}: {m}"
        if sub:
            assert m["subcategory_name"] == sub, f"{text}: {m}"

    def test_detect_no_match(self):
        r = requests.get(f"{BASE_URL}/api/services/detect", params={"text": "zzzz qqqq"})
        assert r.status_code == 200
        assert r.json()["match"] is None


# ---- Provider category aliases ----
class TestProviderAliases:
    @pytest.mark.parametrize("cat,name", [("plumbing-gas", "Sarah Chen"), ("gardening-lawn", "GreenLawn"), ("cleaning", "SparkClean")])
    def test_alias(self, customer, cat, name):
        r = customer.get(f"{BASE_URL}/api/providers/search", params={"category": cat})
        assert r.status_code == 200
        d = r.json()
        items = d if isinstance(d, list) else d.get("providers", d.get("results", []))
        names = [p.get("business_name", "") for p in items]
        assert any(name in n for n in names), f"{cat}: {names}"

    def test_subcategory_keeps_no_sub_providers(self, customer):
        r = customer.get(f"{BASE_URL}/api/providers/search", params={"category": "gardening-lawn", "subcategory": "hedge-trimming"})
        assert r.status_code == 200
        d = r.json()
        items = d if isinstance(d, list) else d.get("providers", d.get("results", []))
        assert any("GreenLawn" in p.get("business_name", "") for p in items)


# ---- Uploads ----
JPG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffdb004300") + b"\x08" * 64 + bytes.fromhex("ffd9")


class TestUploads:
    def test_init_rejects_non_media(self, customer):
        r = customer.post(f"{BASE_URL}/api/uploads/init", json={"filename": "a.pdf", "content_type": "application/pdf", "size": 100})
        assert r.status_code == 400

    def test_init_rejects_too_large(self, customer):
        r = customer.post(f"{BASE_URL}/api/uploads/init", json={"filename": "a.jpg", "content_type": "image/jpeg", "size": 26 * 1024 * 1024})
        assert r.status_code == 400
        r = customer.post(f"{BASE_URL}/api/uploads/init", json={"filename": "a.mp4", "content_type": "video/mp4", "size": 201 * 1024 * 1024})
        assert r.status_code == 400
        r = customer.post(f"{BASE_URL}/api/uploads/init", json={"filename": "a.mp4", "content_type": "video/mp4", "size": 30 * 1024 * 1024})
        assert r.status_code == 200

    def test_init_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/uploads/init", json={"filename": "a.jpg", "content_type": "image/jpeg", "size": 10})
        assert r.status_code == 401

    def test_other_user_cannot_write_chunk(self, customer, provider):
        r = customer.post(f"{BASE_URL}/api/uploads/init", json={"filename": "a.jpg", "content_type": "image/jpeg", "size": len(JPG)})
        uid = r.json()["upload_id"]
        r2 = provider.put(f"{BASE_URL}/api/uploads/{uid}/chunk", params={"index": 0}, data=JPG, headers={"Content-Type": "application/octet-stream"})
        assert r2.status_code == 404

    def test_full_upload_and_range(self, customer):
        half = len(JPG) // 2
        r = customer.post(f"{BASE_URL}/api/uploads/init", json={"filename": "TEST_photo.jpg", "content_type": "image/jpeg", "size": len(JPG)})
        assert r.status_code == 200
        uid = r.json()["upload_id"]
        for i, part in enumerate([JPG[:half], JPG[half:]]):
            c = customer.put(f"{BASE_URL}/api/uploads/{uid}/chunk", params={"index": i}, data=part, headers={"Content-Type": "application/octet-stream"})
            assert c.status_code == 200
        done = customer.post(f"{BASE_URL}/api/uploads/{uid}/complete", params={"total_chunks": 2})
        assert done.status_code == 200, done.text
        d = done.json()
        assert d["url"].startswith("/api/files/") and d["content_type"] == "image/jpeg" and d["file_id"]
        g = customer.get(f"{BASE_URL}{d['url']}")
        assert g.status_code == 200 and g.content == JPG
        assert g.headers["content-type"].startswith("image/jpeg")
        rg = customer.get(f"{BASE_URL}{d['url']}", headers={"Range": "bytes=0-9"})
        assert rg.status_code == 206 and rg.content == JPG[:10]
        assert requests.get(f"{BASE_URL}{d['url']}").status_code == 401
        # second complete must fail (upload consumed)
        assert customer.post(f"{BASE_URL}/api/uploads/{uid}/complete", params={"total_chunks": 2}).status_code == 404
        pytest.uploaded_url = d["url"]

    def test_complete_missing_chunks(self, customer):
        r = customer.post(f"{BASE_URL}/api/uploads/init", json={"filename": "b.jpg", "content_type": "image/jpeg", "size": len(JPG)})
        uid = r.json()["upload_id"]
        assert customer.post(f"{BASE_URL}/api/uploads/{uid}/complete", params={"total_chunks": 1}).status_code == 400

    def test_job_with_new_category_and_media(self, customer):
        url = getattr(pytest, "uploaded_url", None)
        payload = {"title": "TEST_hedge trim", "description": "Hedge overgrown", "category": "gardening-lawn",
                   "subcategory": "hedge-trimming", "photos": [url] if url else []}
        r = customer.post(f"{BASE_URL}/api/jobs", json=payload)
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        g = customer.get(f"{BASE_URL}/api/jobs/{jid}")
        assert g.status_code == 200
        job = g.json()["job"]
        assert job["category"] == "gardening-lawn" and job["photos"] == payload["photos"]
        assert customer.delete(f"{BASE_URL}/api/jobs/{jid}").status_code == 200
