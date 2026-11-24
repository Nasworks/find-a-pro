"""Company team accounts: employee logins, job assignments, GPS timesheets, team board."""
import math
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from html import escape
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

import server as S

router = APIRouter()
DEFAULT_GEOFENCE_M = 150
DEMO_WORKER_EMAIL = "demo-worker@profinder.nz"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _owner_id(user) -> str:
    if user["role"] != "provider":
        raise HTTPException(status_code=403, detail="Only the company (main) account can do this")
    return user["user_id"]


async def _ctx(user) -> Dict[str, Any]:
    """Who the user is within a company: owner or employee."""
    if user["role"] == "provider":
        return {"owner_id": user["user_id"], "member": None, "is_owner": True}
    if user["role"] == "worker":
        member = await S.db.team_members.find_one({"member_id": user.get("member_id"), "owner_id": user.get("employer_id")}, {"_id": 0})
        if not member or not member.get("active", True):
            raise HTTPException(status_code=403, detail="Your team access has been switched off by your company")
        return {"owner_id": user["employer_id"], "member": member, "is_owner": False}
    raise HTTPException(status_code=403, detail="Team accounts only")


async def _worker(user) -> Dict[str, Any]:
    c = await _ctx(user)
    if c["is_owner"]:
        raise HTTPException(status_code=403, detail="Employee login required")
    return c


async def _settings(owner_id: str) -> Dict[str, Any]:
    prof = await S.db.provider_profiles.find_one({"user_id": owner_id}, {"_id": 0, "team_settings": 1, "business_name": 1}) or {}
    s = prof.get("team_settings") or {}
    return {"auto_timesheet_gps": bool(s.get("auto_timesheet_gps", False)),
            "geofence_m": int(s.get("geofence_m") or DEFAULT_GEOFENCE_M),
            "company_name": prof.get("business_name")}


def _dist_m(lat1, lng1, lat2, lng2) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _coords(payload: Dict[str, Any]):
    try:
        lat, lng = float(payload["lat"]), float(payload["lng"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Your location is needed. Allow location access and try again.")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid location")
    return lat, lng


# ---------------- INVITES ----------------
class InviteIn(BaseModel):
    email: Optional[str] = None


@router.post("/team/{member_id}/invite")
async def invite_member(member_id: str, payload: InviteIn, request: Request, user=Depends(S.require_user)):
    owner = _owner_id(user)
    m = await S.db.team_members.find_one({"member_id": member_id, "owner_id": owner}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Team member not found")
    if m.get("linked_user_id"):
        raise HTTPException(status_code=400, detail="This team member already has a login")
    email = (payload.email or m.get("email") or "").strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Add the employee's email address first")
    if await S.db.users.find_one({"email": email}, {"_id": 1}):
        raise HTTPException(status_code=400, detail="That email already has a Pro Finder account. Use a different email for this employee login.")
    token = secrets.token_urlsafe(24)
    await S.db.team_invites.update_many({"member_id": member_id, "used": False}, {"$set": {"used": True, "revoked": True}})
    await S.db.team_invites.insert_one({"token": token, "owner_id": owner, "member_id": member_id, "email": email, "used": False,
                                        "created_at": _now(), "expires_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()})
    await S.db.team_members.update_one({"member_id": member_id}, {"$set": {"email": email, "invite_status": "invited"}})
    origin = (request.headers.get("origin") or "").rstrip("/")
    path = f"/join/{token}"
    sent = False
    if origin.startswith("https://"):
        company = (await _settings(owner))["company_name"] or user.get("name")
        html = (f'<div style="font-family:Arial,sans-serif;color:#111"><h2>{escape(company or "Your company")} added you to their team</h2>'
                f'<p>Hi {escape(m["name"])}, create your employee login to see the jobs sent to you, clock in on site and chat with the team.</p>'
                f'<p><a href="{escape(origin + path)}" style="background:#3b82f6;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none">Create my login</a></p>'
                f'<p style="font-size:12px;color:#888">This link expires in 14 days. We never ask for your password by email.</p></div>')
        try:
            await S.send_email(to=email, subject=f"{company} invited you to Pro Finder NZ", html=html)
            sent = True
        except HTTPException as e:
            S.logger.warning(f"Team invite email failed for {member_id}: {e.detail}")
    return {"invite_path": path, "email": email, "email_sent": sent}


async def _valid_invite(token: str) -> Dict[str, Any]:
    inv = await S.db.team_invites.find_one({"token": token}, {"_id": 0})
    if not inv or inv.get("used") or inv["expires_at"] < _now():
        raise HTTPException(status_code=404, detail="This invite link is invalid or has expired. Ask your company to send a new one.")
    return inv


@router.get("/team/invites/{token}")
async def invite_info(token: str):
    inv = await _valid_invite(token)
    m = await S.db.team_members.find_one({"member_id": inv["member_id"]}, {"_id": 0}) or {}
    return {"email": inv["email"], "name": m.get("name"), "role": m.get("role"),
            "company_name": (await _settings(inv["owner_id"]))["company_name"]}


class AcceptIn(BaseModel):
    password: str
    name: Optional[str] = None


@router.post("/team/invites/{token}/accept")
async def accept_invite(token: str, payload: AcceptIn, response: Response):
    if len(payload.password or "") < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    inv = await S.db.team_invites.find_one_and_update({"token": token, "used": False, "expires_at": {"$gt": _now()}},
                                                      {"$set": {"used": True, "used_at": _now()}})
    if not inv:
        raise HTTPException(status_code=404, detail="This invite link is invalid or has expired.")
    if await S.db.users.find_one({"email": inv["email"]}, {"_id": 1}):
        raise HTTPException(status_code=400, detail="That email already has an account")
    m = await S.db.team_members.find_one({"member_id": inv["member_id"]}, {"_id": 0}) or {}
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {"user_id": user_id, "email": inv["email"], "name": (payload.name or "").strip() or m.get("name") or "Team member",
           "role": "worker", "employer_id": inv["owner_id"], "member_id": inv["member_id"], "phone": m.get("phone"),
           "password_hash": S.hash_password(payload.password), "created_at": datetime.now(timezone.utc), "signup_complete": True}
    await S.db.users.insert_one(doc)
    await S.db.team_members.update_one({"member_id": inv["member_id"]}, {"$set": {"linked_user_id": user_id, "invite_status": "active"}})
    await S.notify(inv["owner_id"], "team_joined", f"{doc['name']} joined your team", "They can now receive jobs and clock in.", "/provider/team")
    tok = S.create_jwt(user_id)
    S.set_auth_cookie(response, tok)
    doc.pop("password_hash")
    doc.pop("_id", None)
    return {"user": doc, "token": tok}


# ---------------- SETTINGS ----------------
class SettingsIn(BaseModel):
    auto_timesheet_gps: bool
    geofence_m: Optional[int] = None


@router.get("/team/settings")
async def get_settings(user=Depends(S.require_user)):
    c = await _ctx(user)
    return await _settings(c["owner_id"])


@router.put("/team/settings")
async def put_settings(payload: SettingsIn, user=Depends(S.require_user)):
    owner = _owner_id(user)
    radius = max(50, min(int(payload.geofence_m or DEFAULT_GEOFENCE_M), 1000))
    await S.db.provider_profiles.update_one({"user_id": owner}, {"$set": {"team_settings": {"auto_timesheet_gps": payload.auto_timesheet_gps, "geofence_m": radius}}})
    return await _settings(owner)


# ---------------- ASSIGNMENTS ----------------
class AssignmentIn(BaseModel):
    member_id: str
    job_id: Optional[str] = None
    title: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    scheduled_for: Optional[str] = None


async def _owner_job(job_id: str, owner: str) -> Dict[str, Any]:
    job = await S.db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    mine = job.get("assigned_provider_id") == owner or await S.db.bookings.find_one({"job_id": job_id, "provider_id": owner}, {"_id": 1}) \
        or await S.db.bids.find_one({"job_id": job_id, "provider_id": owner, "status": {"$in": ["accepted", "completed"]}}, {"_id": 1})
    if not mine:
        raise HTTPException(status_code=403, detail="You can only send your own booked jobs to the team")
    return job


@router.get("/team/jobs")
async def team_jobs(user=Depends(S.require_user)):
    return await S.timesheets_jobs(user=user)


@router.post("/team/assignments")
async def create_assignment(payload: AssignmentIn, user=Depends(S.require_user)):
    owner = _owner_id(user)
    m = await S.db.team_members.find_one({"member_id": payload.member_id, "owner_id": owner}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Team member not found")
    job = await _owner_job(payload.job_id, owner) if payload.job_id else {}
    title = (payload.title or "").strip() or job.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Pick a job or give it a title")
    a = {"assignment_id": f"asg_{uuid.uuid4().hex[:10]}", "owner_id": owner, "member_id": m["member_id"], "member_name": m["name"],
         "job_id": payload.job_id, "title": title, "description": job.get("description"),
         "address": (payload.address or "").strip() or job.get("address") or job.get("location"),
         "latitude": job.get("latitude"), "longitude": job.get("longitude"),
         "notes": (payload.notes or "").strip() or None, "scheduled_for": payload.scheduled_for,
         "status": "assigned", "created_at": _now(), "updated_at": _now()}
    if a["latitude"] is None and a["address"]:
        try:  # site location powers GPS auto-timesheets
            hit = (await S._nominatim_search(a["address"]))[:1]
            if hit and hit[0]["lat"] is not None:
                a["latitude"], a["longitude"] = hit[0]["lat"], hit[0]["lng"]
        except Exception as e:  # noqa: BLE001
            S.logger.info(f"Assignment geocode skipped: {e}")
    await S.db.team_assignments.insert_one(a.copy())
    if m.get("linked_user_id"):
        await S.notify(m["linked_user_id"], "team_job", f"New job: {title}", a["address"] or "", "/worker/jobs")
    return a


async def _with_time(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ids = [a["assignment_id"] for a in items]
    entries = await S.db.time_entries.find({"assignment_id": {"$in": ids}}, {"_id": 0}).to_list(5000)
    for a in items:
        mine = [e for e in entries if e["assignment_id"] == a["assignment_id"]]
        a["minutes_logged"] = round(sum(S._entry_duration_seconds(e) for e in mine) / 60.0, 1)
        a["clocked_in"] = any(e.get("ended_at") is None for e in mine)
    return items


@router.get("/team/assignments")
async def list_assignments(user=Depends(S.require_user)):
    c = await _ctx(user)
    q = {"owner_id": c["owner_id"]} if c["is_owner"] else {"owner_id": c["owner_id"], "member_id": c["member"]["member_id"], "status": {"$ne": "cancelled"}}
    items = await S.db.team_assignments.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return await _with_time(items)


class AssignmentStatusIn(BaseModel):
    status: str


@router.patch("/team/assignments/{assignment_id}")
async def update_assignment(assignment_id: str, payload: AssignmentStatusIn, user=Depends(S.require_user)):
    c = await _ctx(user)
    a = await S.db.team_assignments.find_one({"assignment_id": assignment_id, "owner_id": c["owner_id"]}, {"_id": 0})
    if not a or (not c["is_owner"] and a["member_id"] != c["member"]["member_id"]):
        raise HTTPException(status_code=404, detail="Job not found")
    allowed = {"assigned", "in_progress", "done", "cancelled"} if c["is_owner"] else {"in_progress", "done"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    if payload.status == "done":
        if await S.db.time_entries.find_one({"assignment_id": assignment_id, "ended_at": None}, {"_id": 1}):
            raise HTTPException(status_code=400, detail="Clock out before marking the job done")
        if not c["is_owner"] and not await S.db.time_entries.find_one({"assignment_id": assignment_id}, {"_id": 1}):
            raise HTTPException(status_code=400, detail="A timesheet is required: clock in on site before marking this job done")
    await S.db.team_assignments.update_one({"assignment_id": assignment_id}, {"$set": {"status": payload.status, "updated_at": _now()}})
    if payload.status == "done" and not c["is_owner"]:
        await S.notify(c["owner_id"], "team_job_done", f"{a['member_name']} finished: {a['title']}", "", "/provider/team")
    a["status"] = payload.status
    return a


@router.delete("/team/assignments/{assignment_id}")
async def delete_assignment(assignment_id: str, user=Depends(S.require_user)):
    owner = _owner_id(user)
    res = await S.db.team_assignments.update_one({"assignment_id": assignment_id, "owner_id": owner},
                                                 {"$set": {"status": "cancelled", "updated_at": _now()}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}


# ---------------- WORKER TIMESHEET + GPS ----------------
async def _start_entry(c, a: Dict[str, Any], lat: float, lng: float, mode: str) -> Dict[str, Any]:
    m = c["member"]
    entry = {"entry_id": f"te_{uuid.uuid4().hex[:12]}", "provider_id": c["owner_id"], "worker_id": m["member_id"], "worker_name": m["name"],
             "hourly_rate": float(m.get("hourly_rate") or 45.0), "job_id": a.get("job_id"), "job_title": a["title"], "job_address": a.get("address"),
             "job_latitude": a.get("latitude"), "job_longitude": a.get("longitude"), "assignment_id": a["assignment_id"],
             "type": "work", "mode": mode, "started_at": _now(), "ended_at": None, "started_lat": lat, "started_lng": lng,
             "ended_lat": None, "ended_lng": None, "notes": None, "fuel_km": None, "fuel_cost": None,
             "hourly_rate_snapshot": float(m.get("hourly_rate") or 45.0), "billable": True, "created_at": _now()}
    await S.db.time_entries.insert_one(entry.copy())
    await S.db.team_assignments.update_one({"assignment_id": a["assignment_id"], "status": "assigned"}, {"$set": {"status": "in_progress", "updated_at": _now()}})
    await S.db.team_members.update_one({"member_id": m["member_id"]}, {"$set": {"status": "on_job"}})
    return S._serialize_entry(entry)


async def _stop_entry(c, entry: Dict[str, Any], lat: Optional[float], lng: Optional[float]) -> Dict[str, Any]:
    upd = {"ended_at": _now(), "ended_lat": lat, "ended_lng": lng}
    await S.db.time_entries.update_one({"entry_id": entry["entry_id"]}, {"$set": upd})
    await S.db.team_members.update_one({"member_id": c["member"]["member_id"]}, {"$set": {"status": "available"}})
    entry.update(upd)
    return S._serialize_entry(entry)


async def _running(c) -> Optional[Dict[str, Any]]:
    return await S.db.time_entries.find_one({"provider_id": c["owner_id"], "worker_id": c["member"]["member_id"], "ended_at": None}, {"_id": 0})


async def _locate(c, lat: float, lng: float):
    await S.db.team_members.update_one({"member_id": c["member"]["member_id"]},
                                       {"$set": {"latitude": lat, "longitude": lng, "last_seen_at": _now()}})


class ClockInIn(BaseModel):
    assignment_id: str
    lat: Optional[float] = None
    lng: Optional[float] = None


@router.post("/worker/clock-in")
async def clock_in(payload: ClockInIn, user=Depends(S.require_user)):
    c = await _worker(user)
    lat, lng = _coords(payload.dict())
    a = await S.db.team_assignments.find_one({"assignment_id": payload.assignment_id, "member_id": c["member"]["member_id"],
                                              "status": {"$in": ["assigned", "in_progress"]}}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Job not found or already finished")
    if await _running(c):
        raise HTTPException(status_code=400, detail="You're already clocked in. Clock out first.")
    await _locate(c, lat, lng)
    return {"entry": await _start_entry(c, a, lat, lng, "manual")}


class LocIn(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


@router.post("/worker/clock-out")
async def clock_out(payload: LocIn, user=Depends(S.require_user)):
    c = await _worker(user)
    lat, lng = _coords(payload.dict())
    entry = await _running(c)
    if not entry:
        raise HTTPException(status_code=400, detail="You're not clocked in")
    await _locate(c, lat, lng)
    return {"entry": await _stop_entry(c, entry, lat, lng)}


@router.post("/worker/location")
async def worker_location(payload: LocIn, user=Depends(S.require_user)):
    """Location ping from the employee's phone. Drives auto-timesheets when the company turned them on."""
    c = await _worker(user)
    lat, lng = _coords(payload.dict())
    await _locate(c, lat, lng)
    st = await _settings(c["owner_id"])
    if not st["auto_timesheet_gps"]:
        return {"auto": False, "action": None}
    radius = st["geofence_m"]
    running = await _running(c)
    if running:
        if running.get("mode") == "geofence" and running.get("job_latitude") is not None:
            if _dist_m(lat, lng, running["job_latitude"], running["job_longitude"]) > radius:
                return {"auto": True, "action": "stopped", "entry": await _stop_entry(c, running, lat, lng)}
        return {"auto": True, "action": None}
    open_jobs = await S.db.team_assignments.find({"member_id": c["member"]["member_id"], "status": {"$in": ["assigned", "in_progress"]},
                                                  "latitude": {"$ne": None}}, {"_id": 0}).to_list(100)
    for a in open_jobs:
        if _dist_m(lat, lng, a["latitude"], a["longitude"]) <= radius:
            return {"auto": True, "action": "started", "entry": await _start_entry(c, a, lat, lng, "geofence")}
    return {"auto": True, "action": None}


@router.get("/worker/me")
async def worker_me(user=Depends(S.require_user)):
    c = await _worker(user)
    entries = await S.db.time_entries.find({"provider_id": c["owner_id"], "worker_id": c["member"]["member_id"]}, {"_id": 0}).sort("started_at", -1).to_list(200)
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    week_min = sum(S._entry_duration_seconds(e) for e in entries if e["started_at"] >= week_ago) / 60.0
    running = next((e for e in entries if e.get("ended_at") is None), None)
    m = c["member"]
    return {"member": {k: m.get(k) for k in ("member_id", "name", "role", "hourly_rate")}, "settings": await _settings(c["owner_id"]),
            "running": S._serialize_entry(running) if running else None,
            "entries": [S._serialize_entry(e) for e in entries[:50]], "week_hours": round(week_min / 60.0, 2)}


# ---------------- TEAM BOARD ----------------
class BoardIn(BaseModel):
    text: str = ""
    attachments: List[str] = []


@router.get("/team/board")
async def board(user=Depends(S.require_user)):
    c = await _ctx(user)
    posts = await S.db.team_posts.find({"owner_id": c["owner_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return list(reversed(posts))


@router.post("/team/board")
async def post_board(payload: BoardIn, user=Depends(S.require_user)):
    c = await _ctx(user)
    text = payload.text.strip()[:4000]
    atts = [u for u in payload.attachments if isinstance(u, str) and u.startswith("/api/files/")][:10]
    if not text and not atts:
        raise HTTPException(status_code=400, detail="Write a message or attach a photo")
    post = {"post_id": f"tp_{uuid.uuid4().hex[:10]}", "owner_id": c["owner_id"], "author_id": user["user_id"], "author_name": user.get("name"),
            "is_owner": c["is_owner"], "text": text, "attachments": atts, "created_at": _now()}
    await S.db.team_posts.insert_one(post.copy())
    preview = text[:80] or "Sent a photo"
    if c["is_owner"]:
        linked = await S.db.team_members.find({"owner_id": c["owner_id"], "linked_user_id": {"$ne": None}, "active": True}, {"_id": 0, "linked_user_id": 1}).to_list(200)
        for m in linked:
            if m.get("linked_user_id"):
                await S.notify(m["linked_user_id"], "team_board", f"{user.get('name')} posted on the team board", preview, "/team/board")
    else:
        await S.notify(c["owner_id"], "team_board", f"{user.get('name')} posted on the team board", preview, "/team/board")
    return post


# ---------------- DEMO ----------------
async def ensure_demo_worker() -> Optional[Dict[str, Any]]:
    owner = await S.db.users.find_one({"email": S.DEMO_EMAIL["provider"]}, {"_id": 0, "user_id": 1})
    if not owner:
        return None
    existing = await S.db.users.find_one({"email": DEMO_WORKER_EMAIL})
    if existing:
        return existing
    member_id = f"tm_{uuid.uuid4().hex[:10]}"
    user_id = f"demo_worker_{uuid.uuid4().hex[:8]}"
    await S.db.team_members.insert_one({"member_id": member_id, "owner_id": owner["user_id"], "name": "Sam Taylor", "role": "Apprentice",
                                        "phone": None, "email": DEMO_WORKER_EMAIL, "hourly_rate": 42.0, "active": True, "skills": ["Handyman"],
                                        "status": "available", "latitude": None, "longitude": None, "linked_user_id": user_id,
                                        "invite_status": "active", "created_at": datetime.now(timezone.utc)})
    await S.db.users.insert_one({"user_id": user_id, "email": DEMO_WORKER_EMAIL, "name": "Sam Taylor", "role": "worker",
                                 "employer_id": owner["user_id"], "member_id": member_id, "is_demo": True, "signup_complete": True,
                                 "password_hash": S.hash_password(secrets.token_urlsafe(16)), "created_at": datetime.now(timezone.utc)})
    return await S.db.users.find_one({"email": DEMO_WORKER_EMAIL})
