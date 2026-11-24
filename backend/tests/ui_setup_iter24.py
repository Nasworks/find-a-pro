"""Helper for iter24 UI tests: `setup` creates an assigned job (quote $100) for the demo provider; `cleanup <job_id>` removes it."""
import sys
import uuid
import os
from pathlib import Path
import requests
from pymongo import MongoClient

for _l in list(Path("/app/frontend/.env").read_text().splitlines()) + list(Path("/app/backend/.env").read_text().splitlines()):
    if "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def login(role):
    s = requests.Session()
    r = s.post(f"{API}/auth/demo-login", json={"role": role})
    tok = r.json().get("session_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


if sys.argv[1] == "setup":
    c, p = login("customer"), login("provider")
    jid = c.post(f"{API}/jobs", json={"title": f"TEST_pay_ui_{uuid.uuid4().hex[:5]}", "description": "ui test", "service_type": "residential",
                                      "category": "plumbing-gas", "subcategory": "tap-toilet-repairs", "pricing_type": "small_fixed",
                                      "budget_or_estimate": 100, "location": "1 Queen St, Auckland Central, Auckland"}).json()["job_id"]
    m = next(x for x in p.get(f"{API}/matches/mine").json() if x["job_id"] == jid)
    p.post(f"{API}/matches/{m['match_id']}/accept", json={"message": "hi"})
    print(c.post(f"{API}/jobs/{jid}/award", json={"match_id": m["match_id"]}).status_code, jid)
else:
    jid = sys.argv[2]
    for col in ("bids", "bookings", "job_matches", "job_updates", "invoices", "payment_transactions", "receipts", "time_entries"):
        db[col].delete_many({"job_id": jid})
    db.notifications.delete_many({"link": f"/jobs/{jid}"})
    db.jobs.delete_one({"job_id": jid})
    db.messages.delete_many({"content": {"$regex": "TEST_pay_ui_"}})
    print("cleaned", jid)
