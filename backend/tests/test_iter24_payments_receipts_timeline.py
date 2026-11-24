"""Iter24: Stripe invoice payments (quote/checkout/status/webhook/history), AI receipt scanner + receipts CRUD, project timeline."""
import io
import os
import uuid
import pytest
import requests
from pathlib import Path
from pymongo import MongoClient

for _l in Path("/app/frontend/.env").read_text().splitlines():
    if "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
for _l in Path("/app/backend/.env").read_text().splitlines():
    if "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
DEMO_PRO = "demo_provider_ac7046d0"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CREATED = {"jobs": [], "receipts": [], "files": []}
STATE = {}


def _login(role):
    s = requests.Session()
    r = s.post(f"{API}/auth/demo-login", json={"role": role})
    if r.status_code != 200:
        pytest.skip(f"demo login {role} failed: {r.text}")
    tok = r.json().get("session_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def customer():
    return _login("customer")


@pytest.fixture(scope="module")
def provider():
    return _login("provider")


@pytest.fixture(scope="module")
def landlord():
    return _login("landlord")


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for j in CREATED["jobs"]:
        for c in ("bids", "bookings", "job_matches", "job_updates", "invoices", "payment_transactions", "receipts", "time_entries"):
            db[c].delete_many({"job_id": j})
        db.notifications.delete_many({"link": f"/jobs/{j}"})
        db.jobs.delete_one({"job_id": j})
    for r in CREATED["receipts"]:
        db.receipts.delete_one({"receipt_id": r})
    for f in CREATED["files"]:
        db.files.delete_one({"file_id": f})
    db.messages.delete_many({"content": {"$regex": "TEST_pay_"}})


def _upload(s, data: bytes, name="receipt.png", ct="image/png"):
    r = s.post(f"{API}/uploads/init", json={"filename": name, "content_type": ct, "size": len(data)})
    assert r.status_code == 200, r.text
    uid = r.json()["upload_id"]
    assert s.put(f"{API}/uploads/{uid}/chunk", params={"index": 0}, data=data,
                 headers={"Content-Type": "application/octet-stream"}).status_code == 200
    r = s.post(f"{API}/uploads/{uid}/complete", params={"total_chunks": 1})
    assert r.status_code == 200, r.text
    CREATED["files"].append(r.json()["file_id"])
    return r.json()["url"]


def _receipt_png() -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (520, 760), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        f = ImageFont.load_default()
    lines = ["BUNNINGS WAREHOUSE", "Mt Wellington, Auckland", "GST No: 123-456-789", "Date: 12/01/2026", "",
             "Copper pipe 15mm x3     $45.00", "PVC elbow x4            $12.00", "Plumbers tape           $8.00", "",
             "SUBTOTAL (excl GST)     $56.52", "GST 15%                 $8.48", "TOTAL NZD               $65.00", "",
             "EFTPOS  APPROVED", "Thank you for shopping"]
    y = 30
    for ln in lines:
        d.text((30, y), ln, fill="black", font=f)
        y += 42
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# --- Setup: assigned job for demo provider ---
class TestSetup:
    def test_create_assigned_job(self, customer, provider):
        body = {"title": f"TEST_pay_{uuid.uuid4().hex[:6]}", "description": "test", "service_type": "residential",
                "category": "plumbing-gas", "subcategory": "tap-toilet-repairs", "pricing_type": "small_fixed",
                "budget_or_estimate": 100, "location": "1 Queen St, Auckland Central, Auckland"}
        r = customer.post(f"{API}/jobs", json=body)
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        CREATED["jobs"].append(jid)
        m = next(x for x in provider.get(f"{API}/matches/mine").json() if x["job_id"] == jid)
        assert provider.post(f"{API}/matches/{m['match_id']}/accept", json={"message": "hi"}).status_code == 200
        r = customer.post(f"{API}/jobs/{jid}/award", json={"match_id": m["match_id"]})
        assert r.status_code == 200, r.text
        STATE["job"] = jid


# --- Project timeline ---
class TestTimeline:
    def test_get_defaults(self, customer, provider):
        jid = STATE["job"]
        p = provider.get(f"{API}/jobs/{jid}/timeline").json()
        assert p["current_stage"] == 0 and len(p["stages"]) == 6 and p["can_edit"] is True
        c = customer.get(f"{API}/jobs/{jid}/timeline").json()
        assert c["can_edit"] is False

    def test_permissions_and_validation(self, customer, provider, landlord):
        jid = STATE["job"]
        assert landlord.get(f"{API}/jobs/{jid}/timeline").status_code == 403
        assert customer.post(f"{API}/jobs/{jid}/timeline", json={"message": "x"}).status_code == 403
        assert provider.post(f"{API}/jobs/{jid}/timeline", json={}).status_code == 400
        assert provider.post(f"{API}/jobs/{jid}/timeline", json={"stage_index": 99}).status_code == 400
        assert provider.get(f"{API}/jobs/nope_xyz/timeline").status_code == 404

    def test_stage_move_sets_in_progress_and_notifies(self, customer, provider):
        jid = STATE["job"]
        r = provider.post(f"{API}/jobs/{jid}/timeline", json={"stage_index": 2, "message": "Pipes ordered", "photos": ["http://evil/x.png"]})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["stage"] == "Materials ordered" and d["stage_changed"] is True and d["photos"] == []
        assert db.jobs.find_one({"job_id": jid})["status"] == "in_progress"
        t = customer.get(f"{API}/jobs/{jid}/timeline").json()
        assert t["current_stage"] == 2 and t["updates"][0]["message"] == "Pipes ordered"
        n = customer.get(f"{API}/notifications/mine").json()
        assert any(x["type"] == "job_update" and x["link"] == f"/jobs/{jid}" for x in n["items"])


# --- Receipts ---
class TestReceipts:
    def test_scan_real_ai(self, provider):
        url = _upload(provider, _receipt_png())
        STATE["file_url"] = url
        r = provider.post(f"{API}/receipts/scan", json={"file_url": url}, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        print("SCAN RESULT:", d)
        assert d.get("is_receipt") is True
        assert d.get("total") and abs(float(d["total"]) - 65.0) < 0.01
        assert "bunnings" in (d.get("supplier") or "").lower()
        assert d["suggested_cost_type"] in ("materials", "equipment_purchase", "other")

    def test_scan_validation(self, provider, customer):
        assert provider.post(f"{API}/receipts/scan", json={"file_url": "https://x/y.png"}).status_code == 400
        assert customer.post(f"{API}/receipts/scan", json={"file_url": STATE["file_url"]}).status_code == 403
        assert provider.post(f"{API}/receipts/scan", json={"file_url": "/api/files/file_nope/x.png"}).status_code == 404

    def test_save_validation(self, provider, customer):
        assert provider.post(f"{API}/receipts", json={"cost_type": "bogus", "total": 10}).status_code == 400
        assert provider.post(f"{API}/receipts", json={"cost_type": "materials", "total": 0}).status_code == 400
        assert provider.post(f"{API}/receipts", json={"cost_type": "materials", "total": 10, "job_id": "job_not_mine"}).status_code == 400
        assert customer.post(f"{API}/receipts", json={"cost_type": "materials", "total": 10}).status_code == 403

    def test_save_list_and_invoice_line(self, provider):
        jid = STATE["job"]
        r = provider.post(f"{API}/receipts", json={"file_url": STATE["file_url"], "cost_type": "materials", "supplier": "TEST_Bunnings",
                                                   "date": "2026-01-12", "total": 115.0, "gst": 15.0, "job_id": jid})
        assert r.status_code == 200, r.text
        rid = r.json()["receipt_id"]
        CREATED["receipts"].append(rid)
        assert r.json()["job_title"].startswith("TEST_pay_")
        r2 = provider.post(f"{API}/receipts", json={"cost_type": "fuel", "supplier": "TEST_Z", "total": 23.0})
        CREATED["receipts"].append(r2.json()["receipt_id"])
        lst = provider.get(f"{API}/receipts").json()
        ids = [x["receipt_id"] for x in lst["receipts"]]
        assert rid in ids and r2.json()["receipt_id"] in ids
        assert lst["totals"]["materials"] >= 115.0
        only = provider.get(f"{API}/receipts", params={"job_id": jid}).json()
        assert [x["receipt_id"] for x in only["receipts"]] == [rid]
        inv = provider.get(f"{API}/jobs/{jid}/invoice").json()
        line = next(x for x in inv["lines"] if x.get("receipt_id") == rid)
        assert line["amount"] == 100.0 and line["kind"] == "receipt_materials"
        # quote 100 + receipt ex-GST 100 = 200 subtotal, +15% GST = 230
        assert inv["subtotal"] == 200.0 and inv["total"] == 230.0
        # delete non-job receipt
        assert provider.delete(f"{API}/receipts/{r2.json()['receipt_id']}").status_code == 200
        assert provider.delete(f"{API}/receipts/{r2.json()['receipt_id']}").status_code == 404


# --- Payments ---
class TestPayments:
    def test_quote_before_invoice_400(self, customer):
        assert customer.get(f"{API}/payments/invoice/{STATE['job']}/quote").status_code == 400

    def test_send_invoice_then_quote(self, customer, provider, landlord):
        jid = STATE["job"]
        r = provider.post(f"{API}/jobs/{jid}/invoice/send")
        assert r.status_code == 200, r.text
        assert r.json()["total"] == 230.0
        assert provider.get(f"{API}/payments/invoice/{jid}/quote").status_code == 403
        assert landlord.get(f"{API}/payments/invoice/{jid}/quote").status_code == 403
        q = customer.get(f"{API}/payments/invoice/{jid}/quote").json()
        assert q["invoice_total"] == 230.0 and q["client_platform_fee"] == 11.5
        assert q["total_charge"] == round((230 + 11.5 + 0.30) / 0.973, 2)
        assert q["card_fee"] == round(q["total_charge"] - 241.5, 2)
        assert q["provider_platform_fee"] == 11.5 and q["provider_payout"] == 218.5 and q["paid"] is False

    def test_checkout_creates_stripe_session(self, customer):
        jid = STATE["job"]
        assert customer.post(f"{API}/payments/invoice/{jid}/checkout", json={"origin_url": "javascript:x"}).status_code == 400
        r = customer.post(f"{API}/payments/invoice/{jid}/checkout", json={"origin_url": BASE_URL}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["checkout_url"].startswith("https://") and "stripe" in d["checkout_url"]
        STATE["session"] = d["session_id"]
        tx = db.payment_transactions.find_one({"session_id": d["session_id"]})
        assert tx and tx["payment_status"] == "pending" and tx["amount"] == customer.get(f"{API}/payments/invoice/{jid}/quote").json()["total_charge"]

    def test_status_pending(self, customer):
        r = customer.get(f"{API}/payments/status/{STATE['session']}", timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["payment_status"] in ("pending", "unpaid") and r.json()["job_id"] == STATE["job"]
        assert customer.get(f"{API}/payments/status/cs_nope").status_code == 404

    def test_webhook_rejects_unsigned(self):
        r = requests.post(f"{API}/webhook/stripe", data=b'{"type":"checkout.session.completed"}', headers={"Stripe-Signature": "bad"})
        assert r.status_code == 400

    def test_mark_paid_flow_and_history(self, customer, provider):
        """Simulate a paid session by calling the internal idempotent marker via DB+status path."""
        jid = STATE["job"]
        # Simulate Stripe confirming: flip tx to paid via the same fields _mark_paid writes, then verify side-effects path
        # We cannot complete a real card payment headlessly, so drive _mark_paid directly.
        import asyncio, sys
        sys.path.insert(0, "/app/backend")
        from motor.motor_asyncio import AsyncIOMotorClient
        import server
        server.db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        asyncio.run(server._mark_paid(STATE["session"]))
        job = db.jobs.find_one({"job_id": jid})
        assert job["status"] == "done" and job["payment_status"] == "paid"
        assert db.invoices.find_one({"job_id": jid})["payment_status"] == "paid"
        assert customer.get(f"{API}/payments/invoice/{jid}/quote").json()["paid"] is True
        assert customer.post(f"{API}/payments/invoice/{jid}/checkout", json={"origin_url": BASE_URL}).status_code == 400
        assert provider.post(f"{API}/jobs/{jid}/invoice/send").status_code == 400
        h = customer.get(f"{API}/payments/history").json()
        row = next(x for x in h if x["job_id"] == jid)
        assert row["payment_status"] == "paid" and row["invoice_total"] == 230.0
        hp = provider.get(f"{API}/payments/history").json()
        assert any(x["job_id"] == jid for x in hp)
        n = provider.get(f"{API}/notifications/mine").json()
        assert any(x["type"] == "job_paid" and x["link"] == f"/jobs/{jid}" for x in n["items"])
        st = customer.get(f"{API}/payments/status/{STATE['session']}").json()
        assert st["payment_status"] == "paid"
        # timeline locked on done jobs
        assert provider.post(f"{API}/jobs/{jid}/timeline", json={"message": "late"}).status_code == 400
