"""
Pro Finder NZ Backend - Home Services Marketplace
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Cookie, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Pro Finder NZ API")
api = APIRouter(prefix="/api")


# ---------------- MODELS ----------------
class UserBase(BaseModel):
    email: str
    name: str
    role: str = "customer"  # customer, provider, property, insurance, landlord, facilities
    phone: Optional[str] = None
    picture: Optional[str] = None
    city: Optional[str] = "Auckland"


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class User(UserBase):
    user_id: str
    created_at: datetime


class JobPost(BaseModel):
    job_id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:10]}")
    client_id: str
    title: str
    description: str
    category: str
    subcategory: Optional[str] = None
    service_type: str = "residential"  # residential | commercial
    location: str = "Auckland"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    urgency: str = "flexible"
    mode: str = "quotes"
    status: str = "open"  # open, in_progress, done, cancelled
    photos: List[str] = []
    # ---- Tenant → Manager approval workflow (2026-02-07) ----
    tenancy_id: Optional[str] = None            # set when tenant posts on behalf of a linked tenancy
    tenant_id: Optional[str] = None             # duplicate of client_id, but explicit
    approver_id: Optional[str] = None           # landlord/property/facilities user_id when required
    approval_status: str = "not_required"       # not_required | pending | approved | rejected
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    assigned_provider_id: Optional[str] = None  # manager can pre-assign a preferred provider
    billing_target: str = "client"              # client | approver  — who receives quotes/invoices
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobCreate(BaseModel):
    title: str
    description: str
    category: str
    subcategory: Optional[str] = None
    service_type: str = "residential"
    location: str = "Auckland"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    urgency: str = "flexible"
    mode: str = "quotes"
    photos: List[str] = []
    # Tenant flow: opt-in to route through the manager
    tenancy_id: Optional[str] = None
    route_via_manager: bool = False  # if True and user has active tenancy, will require manager approval


class Tenancy(BaseModel):
    tenancy_id: str = Field(default_factory=lambda: f"ten_{uuid.uuid4().hex[:10]}")
    tenant_id: str
    approver_id: Optional[str] = None       # set when the manager approves — until then, only approver_email is known
    approver_email: str
    approver_role: str = "landlord"          # landlord | property | facilities
    label: Optional[str] = None              # e.g. "12 Grey Lynn Ave — Room 2"
    status: str = "pending"                  # pending | active | rejected | archived
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: Optional[datetime] = None


class TenancyRequestCreate(BaseModel):
    approver_email: EmailStr
    approver_role: str = "landlord"           # landlord | property | facilities
    label: Optional[str] = None


class JobApprovalAction(BaseModel):
    assigned_provider_id: Optional[str] = None  # when approving, optionally pre-assign a specific provider
    open_to_bids: bool = True                   # if False and assigned_provider_id set, only that provider sees it
    reason: Optional[str] = None                # required for reject


class Bid(BaseModel):
    bid_id: str = Field(default_factory=lambda: f"bid_{uuid.uuid4().hex[:10]}")
    job_id: str
    provider_id: str
    provider_name: str
    provider_rating: float = 4.5
    provider_reviews: int = 0
    provider_verified: bool = True
    provider_insured: bool = True
    amount: float
    message: str
    eta_days: int = 3
    start_date: Optional[str] = None
    line_items: List[Dict[str, Any]] = []  # [{label, qty, unit_price, total}]
    terms: str = ""  # payment terms, warranty, exclusions
    documents: List[Dict[str, str]] = []  # [{name, url, size, type}]
    warranty_months: int = 12
    payment_terms: str = "50% upfront, 50% on completion"
    status: str = "pending"  # pending, accepted, rejected, withdrawn, countered
    revision: int = 1
    previous_bid_id: Optional[str] = None  # for counter-offers
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BidCreate(BaseModel):
    job_id: str
    amount: float
    message: str
    eta_days: int = 3
    start_date: Optional[str] = None
    line_items: List[Dict[str, Any]] = []
    terms: str = ""
    documents: List[Dict[str, str]] = []
    warranty_months: int = 12
    payment_terms: str = "50% upfront, 50% on completion"


class BidComment(BaseModel):
    comment_id: str = Field(default_factory=lambda: f"cmt_{uuid.uuid4().hex[:10]}")
    bid_id: str
    author_id: str
    author_name: str
    author_role: str = "client"  # client or provider
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Booking(BaseModel):
    booking_id: str = Field(default_factory=lambda: f"bkg_{uuid.uuid4().hex[:10]}")
    client_id: str
    client_name: str
    provider_id: str
    provider_name: str
    job_id: Optional[str] = None
    category: str
    price: float
    status: str = "booked"  # booked, en_route, working, done, paid, cancelled
    scheduled_at: datetime
    address: str = "Auckland"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BookingCreate(BaseModel):
    provider_id: str
    category: str
    price: float
    scheduled_at: datetime
    address: str = "Auckland"
    job_id: Optional[str] = None


class Message(BaseModel):
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:10]}")
    thread_id: str
    sender_id: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read: bool = False


class MessageCreate(BaseModel):
    thread_id: str
    content: str


class Thread(BaseModel):
    thread_id: str = Field(default_factory=lambda: f"thr_{uuid.uuid4().hex[:10]}")
    participants: List[str]
    participant_names: Dict[str, str] = {}
    subject: str = "Service Request"
    last_message: str = ""
    last_message_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    unread: Dict[str, int] = {}


class ThreadCreate(BaseModel):
    other_user_id: str
    subject: str = "Service Request"
    initial_message: Optional[str] = None


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    original_price: Optional[float] = None
    discount: Optional[int] = None
    image: str
    description: str = ""
    brand: Optional[str] = None
    in_stock: bool = True
    trade_only: bool = False
    rating: float = 4.5
    reviews_count: int = 0


class CartItem(BaseModel):
    product_id: str
    quantity: int = 1


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: f"ord_{uuid.uuid4().hex[:10]}")
    user_id: str
    items: List[Dict[str, Any]]
    total: float
    status: str = "pending"
    address: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedPost(BaseModel):
    post_id: str = Field(default_factory=lambda: f"pst_{uuid.uuid4().hex[:10]}")
    author_id: str
    author_name: str
    author_type: str = "provider"  # provider, admin, system
    author_category: str = "General"
    author_verified: bool = True
    post_type: str = "news"  # sale, news, update, report, article
    title: str
    content: str
    tags: List[str] = []
    likes: int = 0
    liked_by: List[str] = []
    comments_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedPostCreate(BaseModel):
    post_type: str = "news"
    title: str
    content: str
    tags: List[str] = []


class Property(BaseModel):
    property_id: str = Field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:10]}")
    owner_id: str
    address: str
    property_type: str = "residential"
    size: Optional[str] = None
    bedrooms: Optional[int] = None
    tenants: List[Dict[str, str]] = []
    jobs_count: int = 0
    total_spent: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PropertyCreate(BaseModel):
    address: str
    property_type: str = "residential"
    size: Optional[str] = None
    bedrooms: Optional[int] = None


class ProviderProfile(BaseModel):
    user_id: str
    business_name: str
    categories: List[str] = []
    hourly_rate: float = 85.0
    rating: float = 4.7
    reviews_count: int = 0
    jobs_completed: int = 0
    verified: bool = True
    insured: bool = True
    plan: str = "free"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    online: bool = False
    bio: str = ""


# ---------------- AUTH HELPERS ----------------
def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return pwd_ctx.verify(pw, hashed)
    except Exception:
        return False


def create_jwt(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(
    session_token: Optional[str] = Cookie(default=None),
    auth_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> Optional[Dict[str, Any]]:
    """Auth resolution order: session_token cookie → auth_token cookie (JWT) → Authorization header."""
    # 1) OAuth session token (in DB)
    if session_token:
        session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
        if session:
            expires_at = session.get("expires_at")
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if not expires_at or expires_at >= datetime.now(timezone.utc):
                return await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})

    # 2) JWT cookie
    for token in (auth_token, (authorization.split(" ", 1)[1] if authorization and authorization.lower().startswith("bearer ") else None)):
        if not token:
            continue
        # Try DB session first (bearer could carry an OAuth session token from mobile)
        session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
        if session:
            user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})
            if user:
                return user
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            user_id = payload.get("user_id")
            if user_id:
                user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
                if user:
                    return user
        except Exception as e:  # noqa: BLE001
            logging.debug("JWT decode failed: %s", e)
    return None


def set_auth_cookie(response: Response, token: str) -> None:
    """Set httpOnly, secure JWT auth cookie."""
    response.set_cookie(
        key="auth_token",
        value=token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )


async def require_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ---------------- AUTH ROUTES ----------------
@api.post("/auth/register")
async def register(payload: UserCreate, response: Response):
    existing = await db.users.find_one({"email": payload.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id,
        "email": payload.email,
        "name": payload.name,
        "role": payload.role,
        "phone": payload.phone,
        "picture": payload.picture,
        "city": payload.city,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(doc)
    # If provider role, create provider profile
    if payload.role == "provider":
        await db.provider_profiles.insert_one({
            "user_id": user_id,
            "business_name": payload.name,
            "categories": [],
            "hourly_rate": 85.0,
            "rating": 4.7,
            "reviews_count": 0,
            "jobs_completed": 0,
            "verified": True,
            "insured": True,
            "plan": "free",
            "online": False,
            "bio": "",
            "latitude": -36.8485 + (uuid.uuid4().int % 100) / 1000.0,
            "longitude": 174.7633 + (uuid.uuid4().int % 100) / 1000.0,
        })
    token = create_jwt(user_id)
    set_auth_cookie(response, token)
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    return {"user": doc, "token": token}


@api.post("/auth/login")
async def login(payload: UserLogin, response: Response):
    user = await db.users.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(user["user_id"])
    set_auth_cookie(response, token)
    user.pop("_id", None)
    user.pop("password_hash", None)
    return {"user": user, "token": token}


# Demo accounts (idempotent, seeded on startup). One-click preview login by role.
DEMO_ROLES = ["customer", "provider", "property", "landlord", "facilities", "insurance"]
DEMO_EMAIL = {r: f"demo-{r}@profinder.nz" for r in DEMO_ROLES}
DEMO_NAME = {
    "customer": "Demo Customer",
    "provider": "Demo Trade Co.",
    "property": "Demo Property Manager",
    "landlord": "Demo Landlord",
    "facilities": "Demo Facilities Manager",
    "insurance": "Demo Insurance Partner",
}


@api.post("/auth/demo-login")
async def demo_login(request: Request, response: Response):
    """One-click login as a seeded demo account for a given role. Preview-only convenience."""
    body = await request.json()
    role = (body.get("role") or "").strip().lower()
    if role not in DEMO_ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown demo role. Use one of {DEMO_ROLES}")
    user = await db.users.find_one({"email": DEMO_EMAIL[role]})
    if not user:
        # Lazy-provision if the seed hasn't run for some reason.
        await _ensure_demo_account(role)
        user = await db.users.find_one({"email": DEMO_EMAIL[role]})
    if not user:
        raise HTTPException(status_code=500, detail="Failed to provision demo account")
    token = create_jwt(user["user_id"])
    set_auth_cookie(response, token)
    user.pop("_id", None)
    user.pop("password_hash", None)
    return {"user": user, "token": token, "demo": True}


async def _ensure_demo_account(role: str) -> None:
    email = DEMO_EMAIL[role]
    if await db.users.find_one({"email": email}, {"_id": 1}):
        return
    user_id = f"demo_{role}_{uuid.uuid4().hex[:8]}"
    await db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": DEMO_NAME[role],
        "role": role,
        "phone": None,
        "picture": None,
        "city": "Auckland",
        "password_hash": hash_password("Demo123!"),
        "created_at": datetime.now(timezone.utc),
        "is_demo": True,
    })
    if role == "provider":
        await db.provider_profiles.insert_one({
            "user_id": user_id,
            "business_name": DEMO_NAME[role],
            "categories": ["handyman"],
            "subcategories": [],
            "hourly_rate": 75.0,
            "rating": 4.8,
            "reviews_count": 24,
            "jobs_completed": 41,
            "verified": True,
            "insured": True,
            "background_checked": True,
            "accredited": True,
            "plan": "pro",
            "online": True,
            "bio": "Demo provider account — explore the Service Provider dashboard here.",
            "response_time_hours": 2,
            "years_in_business": 6,
            "gallery": [],
            "latitude": -36.8485,
            "longitude": 174.7633,
        })


async def seed_demo_accounts() -> None:
    for r in DEMO_ROLES:
        await _ensure_demo_account(r)


@api.post("/auth/session")
async def google_session(request: Request, response: Response):
    """Emergent Google OAuth session exchange."""
    body = await request.json()
    session_id = body.get("session_id")
    role = body.get("role", "customer")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    async with httpx.AsyncClient() as http:
        r = await http.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=15.0,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        data = r.json()
    email = data.get("email")
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture")
    session_token = data.get("session_token")

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id}, {"$set": {"name": name, "picture": picture}})
        user = existing
        user["name"] = name
        user["picture"] = picture
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": role,
            "phone": None,
            "city": "Auckland",
            "created_at": datetime.now(timezone.utc),
        }
        await db.users.insert_one(user_doc)
        user = user_doc
        if role == "provider":
            await db.provider_profiles.insert_one({
                "user_id": user_id,
                "business_name": name,
                "categories": [],
                "hourly_rate": 85.0,
                "rating": 4.7,
                "reviews_count": 0,
                "jobs_completed": 0,
                "verified": True,
                "insured": True,
                "plan": "free",
                "online": False,
                "bio": "",
                "latitude": -36.8485,
                "longitude": 174.7633,
            })

    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc),
    })

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    user.pop("password_hash", None)
    return {"user": user, "session_token": session_token}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@api.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(default=None)):
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    response.delete_cookie("auth_token", path="/")
    return {"ok": True}


@api.patch("/auth/role")
async def switch_role(request: Request, user=Depends(require_user)):
    body = await request.json()
    role = body.get("role")
    if role not in ["customer", "provider", "property", "insurance", "landlord", "facilities"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"role": role}})
    if role == "provider":
        exists = await db.provider_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if not exists:
            await db.provider_profiles.insert_one({
                "user_id": user["user_id"],
                "business_name": user["name"],
                "categories": [],
                "hourly_rate": 85.0,
                "rating": 4.7,
                "reviews_count": 0,
                "jobs_completed": 0,
                "verified": True,
                "insured": True,
                "plan": "free",
                "online": False,
                "bio": "",
                "latitude": -36.8485,
                "longitude": 174.7633,
            })
    return {"role": role}


# ---------------- JOBS ----------------
@api.post("/jobs")
async def create_job(payload: JobCreate, user=Depends(require_user)):
    # Validate service_type
    if payload.service_type not in ("residential", "commercial"):
        raise HTTPException(status_code=400, detail="service_type must be 'residential' or 'commercial'")
    # Validate category (and subcategory if present) against the correct taxonomy —
    # but stay permissive with legacy short-form categories (from old /api/categories)
    # so we don't break older flows / bookmarks.
    idx = COMMERCIAL_TAXONOMY_INDEX if payload.service_type == "commercial" else RESIDENTIAL_TAXONOMY_INDEX
    known_cats = {k.split("/")[0] for k in idx.keys()}
    if payload.subcategory:
        key = f"{payload.category}/{payload.subcategory}"
        if key not in idx:
            raise HTTPException(status_code=400, detail=f"Unknown subcategory '{payload.subcategory}' for {payload.service_type} category '{payload.category}'")
    elif payload.category in known_cats:
        pass
    # ---- Tenancy / approval routing ----
    approver_id: Optional[str] = None
    tenancy_id: Optional[str] = payload.tenancy_id
    approval_status = "not_required"
    billing_target = "client"
    if payload.route_via_manager or payload.tenancy_id:
        # Find an active tenancy for this tenant. If tenancy_id given, use that;
        # otherwise auto-pick the first active tenancy.
        query: Dict[str, Any] = {"tenant_id": user["user_id"], "status": "active"}
        if payload.tenancy_id:
            query["tenancy_id"] = payload.tenancy_id
        tenancy = await db.tenancies.find_one(query)
        if not tenancy:
            raise HTTPException(status_code=400, detail="No active tenancy found for approval routing")
        approver_id = tenancy.get("approver_id")
        tenancy_id = tenancy["tenancy_id"]
        approval_status = "pending"
        billing_target = "approver"
    job_data = payload.dict(exclude={"route_via_manager", "tenancy_id"})
    job = JobPost(
        client_id=user["user_id"],
        tenant_id=user["user_id"] if approval_status == "pending" else None,
        tenancy_id=tenancy_id,
        approver_id=approver_id,
        approval_status=approval_status,
        billing_target=billing_target,
        **job_data,
    )
    await db.jobs.insert_one(job.dict())
    return job


@api.get("/jobs/mine")
async def my_jobs(user=Depends(require_user)):
    """
    Returns jobs the user is involved with:
    - own posted jobs (as client)
    - jobs where they are the approver (landlord/property/facilities)
    """
    query: Dict[str, Any] = {"$or": [{"client_id": user["user_id"]}]}
    if user["role"] in APPROVER_ROLES:
        query["$or"].append({"approver_id": user["user_id"]})
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    if not jobs:
        return jobs
    # Batch fetch all bids for these jobs (avoids N+1)
    job_ids = [j["job_id"] for j in jobs]
    all_bids = await db.bids.find({"job_id": {"$in": job_ids}}, {"_id": 0}).to_list(None)
    bids_by_job: Dict[str, List[Dict[str, Any]]] = {}
    for b in all_bids:
        bids_by_job.setdefault(b["job_id"], []).append(b)
    for j in jobs:
        bids = bids_by_job.get(j["job_id"], [])
        j["bids_count"] = len(bids)
        if bids:
            amounts = [b["amount"] for b in bids]
            j["bids_range"] = {"min": min(amounts), "max": max(amounts)}
    return jobs


@api.get("/jobs/board")
async def job_board(category: Optional[str] = None, user=Depends(require_user)):
    """Providers only see approved (or not_required) open jobs."""
    q: Dict[str, Any] = {
        "status": "open",
        "approval_status": {"$in": ["not_required", "approved"]},
    }
    if category:
        q["category"] = category
    jobs = await db.jobs.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return jobs


@api.get("/jobs/{job_id}")
async def get_job(job_id: str, user=Depends(require_user)):
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    bids = await db.bids.find({"job_id": job_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"job": job, "bids": bids}


@api.patch("/jobs/{job_id}")
async def update_job(job_id: str, payload: Dict[str, Any], user=Depends(require_user)):
    job = await db.jobs.find_one({"job_id": job_id})
    if not job or job["client_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    allowed = {k: v for k, v in payload.items() if k in ["title", "description", "budget_min", "budget_max", "urgency", "status"]}
    await db.jobs.update_one({"job_id": job_id}, {"$set": allowed})
    updated = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    return updated


@api.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user=Depends(require_user)):
    job = await db.jobs.find_one({"job_id": job_id})
    if not job or job["client_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.jobs.delete_one({"job_id": job_id})
    await db.bids.delete_many({"job_id": job_id})
    return {"ok": True}


# ---------------- BIDS ----------------
@api.post("/bids")
async def create_bid(payload: BidCreate, user=Depends(require_user)):
    job = await db.jobs.find_one({"job_id": payload.job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    profile = await db.provider_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    bid = Bid(
        job_id=payload.job_id,
        provider_id=user["user_id"],
        provider_name=profile.get("business_name") or user["name"],
        provider_rating=profile.get("rating", 4.7),
        provider_reviews=profile.get("reviews_count", 0),
        provider_verified=profile.get("verified", True),
        provider_insured=profile.get("insured", True),
        amount=payload.amount,
        message=payload.message,
        eta_days=payload.eta_days,
        start_date=payload.start_date,
        line_items=payload.line_items,
        terms=payload.terms,
        documents=payload.documents,
        warranty_months=payload.warranty_months,
        payment_terms=payload.payment_terms,
    )
    await db.bids.insert_one(bid.dict())
    return bid


@api.post("/bids/{bid_id}/counter")
async def counter_bid(bid_id: str, payload: BidCreate, user=Depends(require_user)):
    """Client counters a provider bid (or provider revises their bid)."""
    original = await db.bids.find_one({"bid_id": bid_id}, {"_id": 0})
    if not original:
        raise HTTPException(status_code=404, detail="Bid not found")
    job = await db.jobs.find_one({"job_id": original["job_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Mark old bid as countered
    await db.bids.update_one({"bid_id": bid_id}, {"$set": {"status": "countered"}})
    new_bid = Bid(
        job_id=original["job_id"],
        provider_id=original["provider_id"],
        provider_name=original["provider_name"],
        provider_rating=original.get("provider_rating", 4.5),
        provider_reviews=original.get("provider_reviews", 0),
        amount=payload.amount,
        message=payload.message,
        eta_days=payload.eta_days,
        start_date=payload.start_date,
        line_items=payload.line_items,
        terms=payload.terms,
        documents=payload.documents,
        warranty_months=payload.warranty_months,
        payment_terms=payload.payment_terms,
        revision=original.get("revision", 1) + 1,
        previous_bid_id=bid_id,
    )
    await db.bids.insert_one(new_bid.dict())
    # Add an automatic comment for the counter
    await db.bid_comments.insert_one({
        "comment_id": f"cmt_{uuid.uuid4().hex[:10]}",
        "bid_id": new_bid.bid_id,
        "author_id": user["user_id"],
        "author_name": user["name"],
        "author_role": "client" if user["user_id"] == job["client_id"] else "provider",
        "content": f"Counter-offer submitted: ${payload.amount} (was ${original['amount']})",
        "created_at": datetime.now(timezone.utc),
    })
    return new_bid


@api.post("/bids/{bid_id}/reject")
async def reject_bid(bid_id: str, user=Depends(require_user)):
    bid = await db.bids.find_one({"bid_id": bid_id}, {"_id": 0})
    if not bid:
        raise HTTPException(status_code=404, detail="Not found")
    job = await db.jobs.find_one({"job_id": bid["job_id"]}, {"_id": 0})
    if not job or job["client_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.bids.update_one({"bid_id": bid_id}, {"$set": {"status": "rejected"}})
    return {"ok": True}


@api.post("/bids/{bid_id}/withdraw")
async def withdraw_bid(bid_id: str, user=Depends(require_user)):
    bid = await db.bids.find_one({"bid_id": bid_id}, {"_id": 0})
    if not bid or bid["provider_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.bids.update_one({"bid_id": bid_id}, {"$set": {"status": "withdrawn"}})
    return {"ok": True}


@api.get("/bids/{bid_id}/comments")
async def get_bid_comments(bid_id: str, user=Depends(require_user)):
    comments = await db.bid_comments.find({"bid_id": bid_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    return comments


@api.post("/bids/{bid_id}/comments")
async def add_bid_comment(bid_id: str, request: Request, user=Depends(require_user)):
    body = await request.json()
    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Empty content")
    bid = await db.bids.find_one({"bid_id": bid_id}, {"_id": 0})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    job = await db.jobs.find_one({"job_id": bid["job_id"]}, {"_id": 0})
    role = "client" if user["user_id"] == job["client_id"] else "provider"
    doc = {
        "comment_id": f"cmt_{uuid.uuid4().hex[:10]}",
        "bid_id": bid_id,
        "author_id": user["user_id"],
        "author_name": user["name"],
        "author_role": role,
        "content": content,
        "created_at": datetime.now(timezone.utc),
    }
    await db.bid_comments.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.post("/bids/{bid_id}/accept")
async def accept_bid(bid_id: str, user=Depends(require_user)):
    bid = await db.bids.find_one({"bid_id": bid_id}, {"_id": 0})
    if not bid:
        raise HTTPException(status_code=404, detail="Not found")
    job = await db.jobs.find_one({"job_id": bid["job_id"]}, {"_id": 0})
    if not job or job["client_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.bids.update_one({"bid_id": bid_id}, {"$set": {"status": "accepted"}})
    await db.jobs.update_one({"job_id": bid["job_id"]}, {"$set": {"status": "in_progress"}})
    # Create booking
    booking = Booking(
        client_id=user["user_id"],
        client_name=user["name"],
        provider_id=bid["provider_id"],
        provider_name=bid["provider_name"],
        job_id=bid["job_id"],
        category=job["category"],
        price=bid["amount"],
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=bid.get("eta_days", 2)),
        address=job.get("location", "Auckland"),
    )
    await db.bookings.insert_one(booking.dict())
    return booking


@api.get("/bids/mine")
async def my_bids(user=Depends(require_user)):
    bids = await db.bids.find({"provider_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    if not bids:
        return bids
    # Batch fetch all jobs (avoids N+1)
    job_ids = list({b["job_id"] for b in bids})
    jobs = await db.jobs.find({"job_id": {"$in": job_ids}}, {"_id": 0}).to_list(None)
    jobs_map = {j["job_id"]: j for j in jobs}
    for b in bids:
        b["job"] = jobs_map.get(b["job_id"])
    return bids


# ---------------- BOOKINGS ----------------
@api.post("/bookings")
async def create_booking(payload: BookingCreate, user=Depends(require_user)):
    provider = await db.users.find_one({"user_id": payload.provider_id}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    booking = Booking(
        client_id=user["user_id"],
        client_name=user["name"],
        provider_id=payload.provider_id,
        provider_name=provider.get("name"),
        job_id=payload.job_id,
        category=payload.category,
        price=payload.price,
        scheduled_at=payload.scheduled_at,
        address=payload.address,
    )
    await db.bookings.insert_one(booking.dict())
    return booking


@api.get("/bookings/mine")
async def my_bookings(user=Depends(require_user)):
    q = {"$or": [{"client_id": user["user_id"]}, {"provider_id": user["user_id"]}]}
    bookings = await db.bookings.find(q, {"_id": 0}).sort("scheduled_at", -1).to_list(200)
    return bookings


@api.patch("/bookings/{booking_id}/status")
async def update_booking_status(booking_id: str, request: Request, user=Depends(require_user)):
    body = await request.json()
    status = body.get("status")
    if status not in ["booked", "en_route", "working", "done", "paid", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking or (booking["client_id"] != user["user_id"] and booking["provider_id"] != user["user_id"]):
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.bookings.update_one({"booking_id": booking_id}, {"$set": {"status": status}})
    return {"ok": True}


# ---------------- MESSAGES ----------------
@api.post("/threads")
async def create_thread(payload: ThreadCreate, user=Depends(require_user)):
    other = await db.users.find_one({"user_id": payload.other_user_id}, {"_id": 0})
    if not other:
        raise HTTPException(status_code=404, detail="User not found")
    # Check existing
    existing = await db.threads.find_one({
        "participants": {"$all": [user["user_id"], payload.other_user_id]}
    }, {"_id": 0})
    if existing:
        thr = existing
    else:
        thread = Thread(
            participants=[user["user_id"], payload.other_user_id],
            participant_names={user["user_id"]: user["name"], payload.other_user_id: other["name"]},
            subject=payload.subject,
        )
        thr = thread.dict()
        await db.threads.insert_one(thr)
        thr.pop("_id", None)
    if payload.initial_message:
        msg = Message(thread_id=thr["thread_id"], sender_id=user["user_id"], content=payload.initial_message)
        msg_dict = msg.dict()
        await db.messages.insert_one(msg_dict)
        await db.threads.update_one({"thread_id": thr["thread_id"]}, {"$set": {"last_message": payload.initial_message, "last_message_at": msg.timestamp}})
    return thr


@api.get("/threads")
async def list_threads(user=Depends(require_user)):
    threads = await db.threads.find({"participants": user["user_id"]}, {"_id": 0}).sort("last_message_at", -1).to_list(100)
    return threads


@api.get("/threads/{thread_id}/messages")
async def thread_messages(thread_id: str, user=Depends(require_user)):
    thread = await db.threads.find_one({"thread_id": thread_id}, {"_id": 0})
    if not thread or user["user_id"] not in thread["participants"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    msgs = await db.messages.find({"thread_id": thread_id}, {"_id": 0}).sort("timestamp", 1).to_list(500)
    return {"thread": thread, "messages": msgs}


@api.post("/messages")
async def send_message(payload: MessageCreate, user=Depends(require_user)):
    thread = await db.threads.find_one({"thread_id": payload.thread_id}, {"_id": 0})
    if not thread or user["user_id"] not in thread["participants"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    msg = Message(thread_id=payload.thread_id, sender_id=user["user_id"], content=payload.content)
    msg_dict = msg.dict()
    await db.messages.insert_one(msg_dict)
    await db.threads.update_one({"thread_id": payload.thread_id}, {"$set": {"last_message": payload.content, "last_message_at": msg.timestamp}})
    msg_dict.pop("_id", None)
    return msg_dict


# ---------------- PRODUCTS / MARKETPLACE ----------------
@api.get("/products")
async def list_products(category: Optional[str] = None, q: Optional[str] = None):
    query: Dict[str, Any] = {}
    if category:
        query["category"] = category
    if q:
        query["name"] = {"$regex": q, "$options": "i"}
    products = await db.products.find(query, {"_id": 0}).to_list(500)
    return products


@api.get("/products/{product_id}")
async def get_product(product_id: str):
    p = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    return p


@api.post("/orders")
async def create_order(request: Request, user=Depends(require_user)):
    body = await request.json()
    items = body.get("items", [])
    address = body.get("address", user.get("city", "Auckland"))
    total = 0.0
    detailed = []
    for it in items:
        p = await db.products.find_one({"product_id": it["product_id"]}, {"_id": 0})
        if p:
            qty = int(it.get("quantity", 1))
            total += p["price"] * qty
            detailed.append({"product_id": p["product_id"], "name": p["name"], "price": p["price"], "quantity": qty, "image": p["image"]})
    order = Order(user_id=user["user_id"], items=detailed, total=total, address=address)
    await db.orders.insert_one(order.dict())
    return order


@api.get("/orders/mine")
async def my_orders(user=Depends(require_user)):
    orders = await db.orders.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return orders


# ---------------- FEED ----------------
@api.get("/feed")
async def get_feed(post_type: Optional[str] = None):
    q: Dict[str, Any] = {}
    if post_type and post_type != "all":
        q["post_type"] = post_type
    posts = await db.feed_posts.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return posts


@api.post("/feed")
async def create_feed_post(payload: FeedPostCreate, user=Depends(require_user)):
    profile = await db.provider_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    post = FeedPost(
        author_id=user["user_id"],
        author_name=profile.get("business_name") or user["name"],
        author_type="provider" if user["role"] == "provider" else "user",
        author_category=(profile.get("categories") or ["General"])[0] if profile.get("categories") else "General",
        author_verified=True,
        **payload.dict(),
    )
    await db.feed_posts.insert_one(post.dict())
    return post


@api.post("/feed/{post_id}/like")
async def like_post(post_id: str, user=Depends(require_user)):
    post = await db.feed_posts.find_one({"post_id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Not found")
    liked_by = post.get("liked_by", [])
    if user["user_id"] in liked_by:
        liked_by.remove(user["user_id"])
        likes = max(0, post.get("likes", 0) - 1)
    else:
        liked_by.append(user["user_id"])
        likes = post.get("likes", 0) + 1
    await db.feed_posts.update_one({"post_id": post_id}, {"$set": {"liked_by": liked_by, "likes": likes}})
    return {"likes": likes, "liked": user["user_id"] in liked_by}


# ---------------- PROPERTIES ----------------
@api.post("/properties")
async def create_property(payload: PropertyCreate, user=Depends(require_user)):
    prop = Property(owner_id=user["user_id"], **payload.dict())
    await db.properties.insert_one(prop.dict())
    return prop


@api.get("/properties/mine")
async def my_properties(user=Depends(require_user)):
    props = await db.properties.find({"owner_id": user["user_id"]}, {"_id": 0}).to_list(200)
    return props


@api.delete("/properties/{property_id}")
async def delete_property(property_id: str, user=Depends(require_user)):
    p = await db.properties.find_one({"property_id": property_id})
    if not p or p["owner_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.properties.delete_one({"property_id": property_id})
    return {"ok": True}


# ---------------- PROVIDERS ----------------
@api.get("/providers/nearby")
async def nearby_providers(category: Optional[str] = None):
    q: Dict[str, Any] = {}
    if category:
        q["categories"] = category
    profiles = await db.provider_profiles.find(q, {"_id": 0}).to_list(200)
    if not profiles:
        return profiles
    # Batch fetch user records (avoids N+1)
    user_ids = [p["user_id"] for p in profiles]
    users = await db.users.find({"user_id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}).to_list(None)
    users_map = {u["user_id"]: u for u in users}
    for p in profiles:
        u = users_map.get(p["user_id"])
        if u:
            p["name"] = u.get("name")
            p["picture"] = u.get("picture")
    return profiles


# ---------------- PROVIDER DIRECTORY (customer-facing browse & profile) ----------------
def _rate_bucket(hourly_rate: float) -> str:
    if hourly_rate < 60:
        return "low"
    if hourly_rate < 100:
        return "medium"
    return "high"


@api.get("/providers/search")
async def search_providers(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    q: Optional[str] = None,
    min_rating: Optional[float] = None,
    min_reviews: Optional[int] = None,
    min_jobs: Optional[int] = None,
    rate_bucket: Optional[str] = None,   # 'low' | 'medium' | 'high'
    verified_only: bool = False,
    background_checked: bool = False,
    accredited: bool = False,
    sort: str = "best_match",             # best_match | rating | price_asc | price_desc | reviews
    limit: int = 60,
    user=Depends(require_user),
):
    """Customer-facing provider directory search. Filter + sort providers by category/subcategory/etc."""
    query: Dict[str, Any] = {}
    if category:
        query["categories"] = category
    if subcategory:
        query["subcategories"] = subcategory
    if verified_only:
        query["verified"] = True
    if q:
        query["$or"] = [
            {"business_name": {"$regex": q, "$options": "i"}},
            {"bio": {"$regex": q, "$options": "i"}},
        ]
    profiles = await db.provider_profiles.find(query, {"_id": 0}).to_list(500)
    # Hide freshly-registered empty providers from the customer catalog
    # (require a bio OR at least one review to be visible).
    profiles = [p for p in profiles if (p.get("bio") and (p.get("rating") or 0) > 0)]
    # Filter in Python for fields that may not be indexed / stored on the record
    def keep(p: Dict[str, Any]) -> bool:
        if min_rating is not None and (p.get("rating") or 0) < min_rating:
            return False
        if min_reviews is not None and (p.get("reviews_count") or 0) < min_reviews:
            return False
        if min_jobs is not None and (p.get("jobs_completed") or 0) < min_jobs:
            return False
        if rate_bucket:
            b = _rate_bucket(p.get("hourly_rate", 85))
            if b != rate_bucket:
                return False
        if background_checked and not p.get("background_checked", False):
            return False
        if accredited and not p.get("accredited", False):
            return False
        return True
    profiles = [p for p in profiles if keep(p)]
    # Sort
    if sort == "rating":
        profiles.sort(key=lambda p: (p.get("rating", 0), p.get("reviews_count", 0)), reverse=True)
    elif sort == "reviews":
        profiles.sort(key=lambda p: p.get("reviews_count", 0), reverse=True)
    elif sort == "price_asc":
        profiles.sort(key=lambda p: p.get("hourly_rate", 999))
    elif sort == "price_desc":
        profiles.sort(key=lambda p: p.get("hourly_rate", 0), reverse=True)
    else:  # best_match — combines rating * log(reviews+1) with slight boost for verified+high jobs
        import math
        def score(p: Dict[str, Any]) -> float:
            r = p.get("rating", 0)
            rc = p.get("reviews_count", 0)
            jc = p.get("jobs_completed", 0)
            v = 1.1 if p.get("verified") else 1.0
            return (r * (1 + math.log10(rc + 1)) + jc * 0.02) * v
        profiles.sort(key=score, reverse=True)
    profiles = profiles[:limit]
    # Enrich with user picture + hydrate a couple of computed fields
    if profiles:
        ids = [p["user_id"] for p in profiles]
        users = await db.users.find({"user_id": {"$in": ids}}, {"_id": 0, "password_hash": 0}).to_list(None)
        umap = {u["user_id"]: u for u in users}
        saved = await db.saved_providers.find(
            {"user_id": user["user_id"], "provider_id": {"$in": ids}}, {"_id": 0, "provider_id": 1}
        ).to_list(len(ids))
        saved_set = {s["provider_id"] for s in saved}
        for p in profiles:
            u = umap.get(p["user_id"]) or {}
            p["picture"] = u.get("picture")
            p["rate_bucket"] = _rate_bucket(p.get("hourly_rate", 85))
            p["is_saved"] = p["user_id"] in saved_set
    return {"count": len(profiles), "results": profiles}


# ---------------- END PROVIDER DIRECTORY (parametric route defined below /providers/me) ----------------


@api.get("/providers/me")
async def my_provider_profile(user=Depends(require_user)):
    p = await db.provider_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    return p


@api.patch("/providers/me")
async def update_provider(request: Request, user=Depends(require_user)):
    body = await request.json()
    allowed = {k: v for k, v in body.items() if k in ["business_name", "categories", "hourly_rate", "bio", "online", "plan"]}
    await db.provider_profiles.update_one({"user_id": user["user_id"]}, {"$set": allowed}, upsert=True)
    p = await db.provider_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p


@api.get("/providers/{provider_id}")
async def provider_profile(provider_id: str, user=Depends(require_user)):
    p = await db.provider_profiles.find_one({"user_id": provider_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    u = await db.users.find_one({"user_id": provider_id}, {"_id": 0, "password_hash": 0})
    if u:
        p["name"] = u.get("name")
        p["picture"] = u.get("picture")
        p["member_since"] = u.get("created_at")
    p["rate_bucket"] = _rate_bucket(p.get("hourly_rate", 85))
    bids = await db.bids.find({"provider_id": provider_id, "status": {"$in": ["accepted", "completed"]}}, {"_id": 0}).sort("created_at", -1).to_list(20)
    p["past_jobs"] = bids
    reviews = await db.provider_reviews.find({"provider_id": provider_id}, {"_id": 0}).sort("created_at", -1).to_list(30)
    p["reviews"] = reviews
    p["is_saved"] = bool(await db.saved_providers.find_one({"user_id": user["user_id"], "provider_id": provider_id}))
    return p


# ---------------- SAVED PROVIDERS ("My Saved Pros") ----------------
@api.get("/saved-providers")
async def list_saved_providers(user=Depends(require_user)):
    """Return the current user's saved (bookmarked) provider profiles as full cards."""
    saved = await db.saved_providers.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("saved_at", -1).to_list(200)
    if not saved:
        return {"count": 0, "results": []}
    ids = [s["provider_id"] for s in saved]
    profiles = await db.provider_profiles.find({"user_id": {"$in": ids}}, {"_id": 0}).to_list(len(ids))
    users = await db.users.find({"user_id": {"$in": ids}}, {"_id": 0, "password_hash": 0}).to_list(None)
    umap = {u["user_id"]: u for u in users}
    pmap: Dict[str, Dict[str, Any]] = {}
    for p in profiles:
        u = umap.get(p["user_id"]) or {}
        p["picture"] = u.get("picture")
        p["rate_bucket"] = _rate_bucket(p.get("hourly_rate", 85))
        pmap[p["user_id"]] = p
    # Preserve insertion order (most recently saved first) and drop any orphan ids.
    ordered: List[Dict[str, Any]] = []
    saved_at_map = {s["provider_id"]: s.get("saved_at") for s in saved}
    for s in saved:
        card = pmap.get(s["provider_id"])
        if not card:
            continue
        card["saved_at"] = saved_at_map.get(s["provider_id"])
        ordered.append(card)
    return {"count": len(ordered), "results": ordered}


@api.post("/saved-providers/{provider_id}")
async def save_provider(provider_id: str, user=Depends(require_user)):
    if provider_id == user["user_id"]:
        raise HTTPException(status_code=400, detail="You cannot save your own profile")
    exists = await db.provider_profiles.find_one({"user_id": provider_id}, {"_id": 0, "user_id": 1})
    if not exists:
        raise HTTPException(status_code=404, detail="Provider not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.saved_providers.update_one(
        {"user_id": user["user_id"], "provider_id": provider_id},
        {"$setOnInsert": {"user_id": user["user_id"], "provider_id": provider_id, "saved_at": now}},
        upsert=True,
    )
    return {"saved": True, "provider_id": provider_id}


@api.delete("/saved-providers/{provider_id}")
async def unsave_provider(provider_id: str, user=Depends(require_user)):
    res = await db.saved_providers.delete_one({"user_id": user["user_id"], "provider_id": provider_id})
    return {"saved": False, "removed": res.deleted_count, "provider_id": provider_id}


# ---------------- DASHBOARD STATS ----------------
@api.get("/stats/customer")
async def customer_stats(user=Depends(require_user)):
    bookings = await db.bookings.find({"client_id": user["user_id"]}, {"_id": 0}).to_list(500)
    total_spent = sum(b["price"] for b in bookings if b.get("status") == "paid")
    completed = sum(1 for b in bookings if b.get("status") in ["done", "paid"])
    active = sum(1 for b in bookings if b.get("status") in ["booked", "en_route", "working"])
    upcoming = sum(1 for b in bookings if b.get("status") == "booked")
    unpaid = sum(1 for b in bookings if b.get("status") == "done")
    return {
        "total_spent": total_spent,
        "jobs_done": completed,
        "active_jobs": active,
        "upcoming": upcoming,
        "unpaid": unpaid,
        "avg_cost": total_spent / completed if completed else 0,
    }


@api.get("/stats/provider")
async def provider_stats(user=Depends(require_user)):
    bookings = await db.bookings.find({"provider_id": user["user_id"]}, {"_id": 0}).to_list(500)
    earnings = sum(b["price"] for b in bookings if b.get("status") == "paid")
    jobs_done = sum(1 for b in bookings if b.get("status") in ["done", "paid"])
    active = sum(1 for b in bookings if b.get("status") in ["booked", "en_route", "working"])
    pending_bids = await db.bids.count_documents({"provider_id": user["user_id"], "status": "pending"})
    return {
        "earnings": earnings,
        "jobs_done": jobs_done,
        "active_jobs": active,
        "pending_bids": pending_bids,
    }


# ---------------- QUOTATIONS ----------------
class Quotation(BaseModel):
    quote_id: str = Field(default_factory=lambda: f"quo_{uuid.uuid4().hex[:10]}")
    provider_id: str
    client_id: Optional[str] = None
    client_name: str
    title: str
    description: str = ""
    line_items: List[Dict[str, Any]] = []
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    valid_until: Optional[str] = None
    status: str = "draft"  # draft, sent, accepted, rejected, expired
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@api.post("/quotations")
async def create_quote(request: Request, user=Depends(require_user)):
    body = await request.json()
    items = body.get("line_items", [])
    subtotal = sum(float(i.get("qty", 1)) * float(i.get("unit_price", 0)) for i in items)
    tax = round(subtotal * 0.15, 2)
    total = round(subtotal + tax, 2)
    q = Quotation(
        provider_id=user["user_id"],
        client_id=body.get("client_id"),
        client_name=body.get("client_name", "Client"),
        title=body.get("title", "Quote"),
        description=body.get("description", ""),
        line_items=items,
        subtotal=subtotal,
        tax=tax,
        total=total,
        valid_until=body.get("valid_until"),
        status=body.get("status", "draft"),
    )
    await db.quotations.insert_one(q.dict())
    return q


@api.get("/quotations/mine")
async def list_quotes(user=Depends(require_user)):
    quotes = await db.quotations.find({"provider_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return quotes


@api.patch("/quotations/{quote_id}")
async def update_quote(quote_id: str, request: Request, user=Depends(require_user)):
    body = await request.json()
    q = await db.quotations.find_one({"quote_id": quote_id})
    if not q or q["provider_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    allowed = {k: v for k, v in body.items() if k in ["status", "title", "description", "line_items", "valid_until"]}
    if "line_items" in allowed:
        items = allowed["line_items"]
        allowed["subtotal"] = sum(float(i.get("qty", 1)) * float(i.get("unit_price", 0)) for i in items)
        allowed["tax"] = round(allowed["subtotal"] * 0.15, 2)
        allowed["total"] = round(allowed["subtotal"] + allowed["tax"], 2)
    await db.quotations.update_one({"quote_id": quote_id}, {"$set": allowed})
    updated = await db.quotations.find_one({"quote_id": quote_id}, {"_id": 0})
    return updated


@api.delete("/quotations/{quote_id}")
async def delete_quote(quote_id: str, user=Depends(require_user)):
    q = await db.quotations.find_one({"quote_id": quote_id})
    if not q or q["provider_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.quotations.delete_one({"quote_id": quote_id})
    return {"ok": True}


# ---------------- TEAM MEMBERS ----------------
class TeamMember(BaseModel):
    member_id: str = Field(default_factory=lambda: f"tm_{uuid.uuid4().hex[:10]}")
    owner_id: str
    name: str
    role: str = "Worker"
    phone: Optional[str] = None
    email: Optional[str] = None
    hourly_rate: float = 45.0
    active: bool = True
    skills: List[str] = []
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str = "available"  # available, on_job, off_duty
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@api.post("/team")
async def add_team_member(payload: Dict[str, Any], user=Depends(require_user)):
    m = TeamMember(owner_id=user["user_id"], **{k: v for k, v in payload.items() if k in ["name", "role", "phone", "email", "hourly_rate", "skills"]})
    await db.team_members.insert_one(m.dict())
    return m


@api.get("/team")
async def list_team(user=Depends(require_user)):
    members = await db.team_members.find({"owner_id": user["user_id"]}, {"_id": 0}).to_list(200)
    return members


@api.patch("/team/{member_id}")
async def update_team_member(member_id: str, payload: Dict[str, Any], user=Depends(require_user)):
    m = await db.team_members.find_one({"member_id": member_id})
    if not m or m["owner_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    allowed = {k: v for k, v in payload.items() if k in ["name", "role", "phone", "hourly_rate", "active", "skills", "status"]}
    await db.team_members.update_one({"member_id": member_id}, {"$set": allowed})
    return await db.team_members.find_one({"member_id": member_id}, {"_id": 0})


@api.delete("/team/{member_id}")
async def delete_team_member(member_id: str, user=Depends(require_user)):
    m = await db.team_members.find_one({"member_id": member_id})
    if not m or m["owner_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.team_members.delete_one({"member_id": member_id})
    return {"ok": True}


# ---------------- TRADES BOARD (provider-to-provider jobs) ----------------
class TradeJob(BaseModel):
    trade_job_id: str = Field(default_factory=lambda: f"tj_{uuid.uuid4().hex[:10]}")
    poster_id: str
    poster_name: str
    title: str
    description: str
    trade: str  # e.g. sparky, plumber, chippie
    location: str = "Auckland"
    budget: Optional[float] = None
    urgency: str = "flexible"
    status: str = "open"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@api.post("/trades-board")
async def create_trade_job(payload: Dict[str, Any], user=Depends(require_user)):
    t = TradeJob(
        poster_id=user["user_id"],
        poster_name=user["name"],
        title=payload.get("title"),
        description=payload.get("description"),
        trade=payload.get("trade", "handyman"),
        location=payload.get("location", "Auckland"),
        budget=payload.get("budget"),
        urgency=payload.get("urgency", "flexible"),
    )
    await db.trade_jobs.insert_one(t.dict())
    return t


@api.get("/trades-board")
async def list_trade_jobs(user=Depends(require_user)):
    jobs = await db.trade_jobs.find({"status": "open"}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return jobs


# ---------------- EXTERNAL JOBS (leads from partners) ----------------
@api.get("/external-jobs")
async def external_jobs(user=Depends(require_user)):
    """Returns mocked partner leads."""
    jobs = await db.external_jobs.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return jobs


# ---------------- GPS DEVICES ----------------
class GpsDevice(BaseModel):
    device_id: str = Field(default_factory=lambda: f"gps_{uuid.uuid4().hex[:8]}")
    owner_id: str
    name: str
    assigned_to: Optional[str] = None  # member_id
    battery: int = 100
    latitude: float = -36.8485
    longitude: float = 174.7633
    last_update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True


@api.get("/gps-devices")
async def list_gps(user=Depends(require_user)):
    devices = await db.gps_devices.find({"owner_id": user["user_id"]}, {"_id": 0}).to_list(200)
    return devices


@api.post("/gps-devices")
async def add_gps(payload: Dict[str, Any], user=Depends(require_user)):
    d = GpsDevice(owner_id=user["user_id"], name=payload.get("name", "New device"), assigned_to=payload.get("assigned_to"))
    await db.gps_devices.insert_one(d.dict())
    return d


# ---------------- MEMBERSHIP ----------------
MEMBERSHIP_PLANS = [
    {"id": "free", "name": "Free", "price": 0, "period": "forever", "features": ["Basic profile", "5 bids/month", "Standard listing", "Email support"], "limits": {"bids": 5, "listing": "standard"}},
    {"id": "starter", "name": "Starter", "price": 49, "period": "month", "features": ["Verified badge", "25 bids/month", "Priority in search", "Chat with clients", "Basic analytics"], "limits": {"bids": 25, "listing": "priority"}, "popular": False},
    {"id": "pro", "name": "Pro", "price": 99, "period": "month", "features": ["Unlimited bids", "Featured placement", "Multi-worker team", "Advanced analytics", "GPS tracking (2 devices)", "Priority support"], "limits": {"bids": -1, "listing": "featured"}, "popular": True},
    {"id": "enterprise", "name": "Enterprise", "price": 299, "period": "month", "features": ["Everything in Pro", "Unlimited team & devices", "API access", "Dedicated account manager", "Custom branding", "White-glove onboarding"], "limits": {"bids": -1, "listing": "featured"}},
]


@api.get("/membership/plans")
async def get_plans():
    return MEMBERSHIP_PLANS


@api.get("/membership/mine")
async def my_membership(user=Depends(require_user)):
    profile = await db.provider_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    plan_id = profile.get("plan", "free")
    plan = next((p for p in MEMBERSHIP_PLANS if p["id"] == plan_id), MEMBERSHIP_PLANS[0])
    return {"plan": plan, "bids_used_this_month": await db.bids.count_documents({"provider_id": user["user_id"]}) or 0}


@api.post("/membership/subscribe")
async def subscribe(payload: Dict[str, str], user=Depends(require_user)):
    plan_id = payload.get("plan_id", "free")
    if plan_id not in [p["id"] for p in MEMBERSHIP_PLANS]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    await db.provider_profiles.update_one({"user_id": user["user_id"]}, {"$set": {"plan": plan_id}}, upsert=True)
    plan = next(p for p in MEMBERSHIP_PLANS if p["id"] == plan_id)
    return {"plan": plan}


# ---------------- WARRANTY CLAIMS ----------------
class WarrantyClaim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"wc_{uuid.uuid4().hex[:10]}")
    user_id: str
    booking_id: Optional[str] = None
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None
    subject: str
    description: str
    status: str = "open"  # open, in_review, resolved, denied
    photos: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@api.post("/warranty-claims")
async def create_claim(payload: Dict[str, Any], user=Depends(require_user)):
    c = WarrantyClaim(
        user_id=user["user_id"],
        booking_id=payload.get("booking_id"),
        provider_id=payload.get("provider_id"),
        provider_name=payload.get("provider_name"),
        subject=payload.get("subject", "Warranty issue"),
        description=payload.get("description", ""),
        photos=payload.get("photos", []),
    )
    await db.warranty_claims.insert_one(c.dict())
    return c


@api.get("/warranty-claims/mine")
async def my_claims(user=Depends(require_user)):
    claims = await db.warranty_claims.find({"$or": [{"user_id": user["user_id"]}, {"provider_id": user["user_id"]}]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return claims


# ---------------- REFERRALS ----------------
@api.get("/referrals/mine")
async def my_referrals(user=Depends(require_user)):
    """Returns referrals passed to me and passed by me."""
    incoming = await db.referrals.find({"referred_to": user["user_id"]}, {"_id": 0}).to_list(100)
    outgoing = await db.referrals.find({"referred_by": user["user_id"]}, {"_id": 0}).to_list(100)
    # Generate a personal invite code
    code = user["user_id"][-6:].upper()
    return {"incoming": incoming, "outgoing": outgoing, "invite_code": code, "reward_per_signup": 25}


# ---------------- JOB HISTORY ----------------
@api.get("/job-history")
async def job_history(user=Depends(require_user)):
    q = {"$or": [{"client_id": user["user_id"]}, {"provider_id": user["user_id"]}], "status": {"$in": ["done", "paid", "cancelled"]}}
    bookings = await db.bookings.find(q, {"_id": 0}).sort("scheduled_at", -1).to_list(500)
    return bookings


# ---------------- TENANCY & APPROVAL WORKFLOW ----------------
APPROVER_ROLES = {"landlord", "property", "facilities"}


def _serialize_tenancy(t: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in t.items() if k != "_id"}


@api.post("/tenancies")
async def create_tenancy_request(payload: TenancyRequestCreate, user=Depends(require_user)):
    """A tenant/customer requests to link with a landlord/property manager by email."""
    if payload.approver_role not in APPROVER_ROLES:
        raise HTTPException(status_code=400, detail=f"approver_role must be one of {sorted(APPROVER_ROLES)}")
    approver_email = payload.approver_email.lower()
    # If an approver with this email already exists, pre-link the approver_id
    approver = await db.users.find_one({"email": approver_email})
    approver_id = approver["user_id"] if approver else None
    # Prevent duplicate pending/active links for the same (tenant, email)
    existing = await db.tenancies.find_one({
        "tenant_id": user["user_id"], "approver_email": approver_email, "status": {"$in": ["pending", "active"]},
    })
    if existing:
        return _serialize_tenancy(existing)
    tenancy = Tenancy(
        tenant_id=user["user_id"],
        approver_id=approver_id,
        approver_email=approver_email,
        approver_role=payload.approver_role,
        label=payload.label,
    )
    await db.tenancies.insert_one(tenancy.dict())
    return tenancy.dict()


@api.get("/tenancies/mine")
async def my_tenancies(user=Depends(require_user)):
    """
    - Tenant sees tenancies where they are the tenant.
    - Approver sees tenancies where their user_id OR email matches.
    """
    if user["role"] in APPROVER_ROLES:
        cursor = db.tenancies.find({"$or": [
            {"approver_id": user["user_id"]},
            {"approver_email": user["email"].lower()},
        ]})
    else:
        cursor = db.tenancies.find({"tenant_id": user["user_id"]})
    items = await cursor.sort("created_at", -1).to_list(200)
    # Enrich with the counterparty name for UI
    out = []
    for t in items:
        tenant = await db.users.find_one({"user_id": t.get("tenant_id")}, {"_id": 0, "user_id": 1, "name": 1, "email": 1})
        approver = None
        if t.get("approver_id"):
            approver = await db.users.find_one({"user_id": t["approver_id"]}, {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1})
        item = _serialize_tenancy(t)
        item["tenant"] = tenant
        item["approver"] = approver
        out.append(item)
    return out


async def _require_tenancy_approver(tenancy_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    t = await db.tenancies.find_one({"tenancy_id": tenancy_id})
    if not t:
        raise HTTPException(status_code=404, detail="Tenancy not found")
    matches = t.get("approver_id") == user["user_id"] or t.get("approver_email") == user["email"].lower()
    if not matches:
        raise HTTPException(status_code=403, detail="You are not the approver on this tenancy")
    if user["role"] not in APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Your role cannot approve tenancies")
    return t


@api.post("/tenancies/{tenancy_id}/approve")
async def approve_tenancy(tenancy_id: str, user=Depends(require_user)):
    t = await _require_tenancy_approver(tenancy_id, user)
    if t["status"] == "active":
        return _serialize_tenancy(t)
    now = datetime.now(timezone.utc)
    await db.tenancies.update_one(
        {"tenancy_id": tenancy_id},
        {"$set": {"status": "active", "approver_id": user["user_id"], "approved_at": now}},
    )
    updated = await db.tenancies.find_one({"tenancy_id": tenancy_id})
    return _serialize_tenancy(updated)


@api.post("/tenancies/{tenancy_id}/reject")
async def reject_tenancy(tenancy_id: str, user=Depends(require_user)):
    await _require_tenancy_approver(tenancy_id, user)
    await db.tenancies.update_one({"tenancy_id": tenancy_id}, {"$set": {"status": "rejected"}})
    return {"ok": True}


@api.delete("/tenancies/{tenancy_id}")
async def archive_tenancy(tenancy_id: str, user=Depends(require_user)):
    t = await db.tenancies.find_one({"tenancy_id": tenancy_id})
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    is_tenant = t.get("tenant_id") == user["user_id"]
    is_approver = t.get("approver_id") == user["user_id"] or t.get("approver_email") == user["email"].lower()
    if not (is_tenant or is_approver):
        raise HTTPException(status_code=403, detail="Not your tenancy")
    await db.tenancies.update_one({"tenancy_id": tenancy_id}, {"$set": {"status": "archived"}})
    return {"ok": True}


async def _preferred_providers_for_approver(approver_id: str) -> List[Dict[str, Any]]:
    """Distinct providers who have completed / accepted bids on this approver's past jobs."""
    approver_jobs = await db.jobs.find({"approver_id": approver_id}, {"job_id": 1, "_id": 0}).to_list(500)
    job_ids = [j["job_id"] for j in approver_jobs]
    if not job_ids:
        return []
    bids = await db.bids.find({"job_id": {"$in": job_ids}, "status": {"$in": ["accepted", "completed"]}}).to_list(500)
    provider_ids = list({b["provider_id"] for b in bids})
    if not provider_ids:
        return []
    profiles = await db.provider_profiles.find({"user_id": {"$in": provider_ids}}).to_list(500)
    return [{"user_id": p["user_id"], "business_name": p.get("business_name"), "rating": p.get("rating", 0), "reviews": p.get("reviews", 0)} for p in profiles]


@api.get("/approvals/preferred-providers")
async def preferred_providers(user=Depends(require_user)):
    if user["role"] not in APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Only approvers can view preferred providers")
    return await _preferred_providers_for_approver(user["user_id"])


@api.get("/approvals/queue")
async def approval_queue(user=Depends(require_user)):
    """Jobs awaiting this approver's decision."""
    if user["role"] not in APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Only approvers can view approval queue")
    jobs = await db.jobs.find({
        "approver_id": user["user_id"],
        "approval_status": "pending",
    }).sort("created_at", -1).to_list(200)
    # Enrich with tenant info
    out = []
    for j in jobs:
        tenant = await db.users.find_one({"user_id": j.get("tenant_id")}, {"_id": 0, "user_id": 1, "name": 1, "email": 1})
        item = {k: v for k, v in j.items() if k != "_id"}
        item["tenant"] = tenant
        out.append(item)
    return out


@api.post("/jobs/{job_id}/approve")
async def approve_job(job_id: str, payload: JobApprovalAction, user=Depends(require_user)):
    job = await db.jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("approver_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your approval to make")
    if job.get("approval_status") != "pending":
        raise HTTPException(status_code=400, detail=f"Job is not pending (status: {job.get('approval_status')})")
    update: Dict[str, Any] = {
        "approval_status": "approved",
        "approved_at": datetime.now(timezone.utc),
        "billing_target": "approver",
    }
    if payload.assigned_provider_id:
        # Validate provider exists
        provider = await db.provider_profiles.find_one({"user_id": payload.assigned_provider_id})
        if not provider:
            raise HTTPException(status_code=400, detail="Assigned provider not found")
        update["assigned_provider_id"] = payload.assigned_provider_id
        if not payload.open_to_bids:
            update["mode"] = "instant"
    await db.jobs.update_one({"job_id": job_id}, {"$set": update})
    updated = await db.jobs.find_one({"job_id": job_id})
    return {k: v for k, v in updated.items() if k != "_id"}


@api.post("/jobs/{job_id}/reject")
async def reject_job(job_id: str, payload: JobApprovalAction, user=Depends(require_user)):
    job = await db.jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("approver_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your rejection to make")
    if job.get("approval_status") != "pending":
        raise HTTPException(status_code=400, detail=f"Job is not pending (status: {job.get('approval_status')})")
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    await db.jobs.update_one({"job_id": job_id}, {"$set": {
        "approval_status": "rejected",
        "rejection_reason": payload.reason.strip(),
        "status": "cancelled",
    }})
    return {"ok": True}


# ---------------- COMMERCIAL SERVICES TAXONOMY ----------------
RESIDENTIAL_TAXONOMY = [
    {"id": "general-home-maintenance", "name": "General Home Maintenance", "icon": "Home", "color": "#3B82F6", "subs": [
        "Handyman Services", "Home Repairs", "Property Maintenance",
        "Preventative Maintenance", "Odd Jobs", "Home Improvements",
    ]},
    {"id": "electrical", "name": "Electrical", "icon": "Zap", "color": "#F59E0B", "subs": [
        "Residential Electrical", "New Wiring & Rewiring", "Lighting Installation",
        "Power Points & Switches", "Switchboard Upgrades", "EV Charger Installation",
        "Smoke Alarms", "Fault Finding & Repairs",
    ]},
    {"id": "plumbing-gas", "name": "Plumbing & Gas", "icon": "Droplets", "color": "#0EA5E9", "subs": [
        "Residential Plumbing", "Blocked Drains", "Leak Repairs", "Hot Water Systems",
        "Tap & Toilet Repairs", "Bathroom Plumbing", "Kitchen Plumbing", "Gas Fitting & Gas Appliances",
    ]},
    {"id": "heating-cooling-ventilation", "name": "Heating, Cooling & Ventilation", "icon": "Wind", "color": "#06B6D4", "subs": [
        "Heat Pump Installation", "Air Conditioning", "Home Ventilation Systems",
        "Bathroom Extractor Fans", "Ducted Heating", "HVAC Servicing",
    ]},
    {"id": "roofing-guttering", "name": "Roofing & Guttering", "icon": "Home", "color": "#EF4444", "subs": [
        "Roof Repairs", "Roof Replacement", "Gutter Repairs", "Gutter Replacement",
        "Downpipes", "Roof Leak Repairs", "Skylight Installation",
    ]},
    {"id": "carpentry-joinery", "name": "Carpentry & Joinery", "icon": "Hammer", "color": "#A16207", "subs": [
        "General Carpentry", "Deck Construction", "Pergolas", "Fencing",
        "Doors", "Windows", "Built-in Cabinets", "Kitchen Cabinetry",
    ]},
    {"id": "painting-interior-finishes", "name": "Painting & Interior Finishes", "icon": "Paintbrush", "color": "#EC4899", "subs": [
        "Interior Painting", "Exterior Painting", "Gib Installation", "Gib Stopping",
        "Plastering", "Wallpaper Installation", "Ceiling Repairs",
    ]},
    {"id": "flooring-tiling", "name": "Flooring & Tiling", "icon": "Grid3x3", "color": "#F97316", "subs": [
        "Timber Flooring", "Laminate Flooring", "Vinyl Flooring", "Carpet Installation",
        "Floor Repairs", "Floor & Wall Tiling", "Bathroom Tiling", "Kitchen Splashbacks",
    ]},
    {"id": "kitchens-bathrooms-renovations", "name": "Kitchens, Bathrooms & Renovations", "icon": "Sparkles", "color": "#8B5CF6", "subs": [
        "Kitchen Renovations", "Bathroom Renovations", "Laundry Renovations",
        "Home Alterations", "Room Additions", "Home Extensions", "Interior Refurbishments",
    ]},
    {"id": "concrete-outdoor-construction", "name": "Concrete & Outdoor Construction", "icon": "Layers", "color": "#71717A", "subs": [
        "Driveways", "Paths", "Concrete Slabs", "Retaining Walls",
        "Paving", "Excavation", "Site Preparation",
    ]},
    {"id": "glass-windows", "name": "Glass & Windows", "icon": "Square", "color": "#0891B2", "subs": [
        "Glass Replacement", "Double Glazing", "Window Installation",
        "Shower Glass", "Mirrors", "Glass Balustrades",
    ]},
    {"id": "security-smart-home", "name": "Security & Smart Home", "icon": "ShieldCheck", "color": "#7C3AED", "subs": [
        "CCTV Installation", "Alarm Systems", "Smart Doorbells", "Smart Locks",
        "Intercom Systems", "Access Control", "Home Automation",
    ]},
    {"id": "data-communications", "name": "Data & Communications", "icon": "Router", "color": "#2563EB", "subs": [
        "Wi-Fi Installation", "Data Cabling", "Fibre Cabling",
        "TV Wall Mounting", "Home Networking", "Audio & Visual Installation",
    ]},
    {"id": "solar-energy", "name": "Solar & Energy", "icon": "Sun", "color": "#10B981", "subs": [
        "Solar Panel Installation", "Home Battery Installation", "EV Chargers",
        "Energy Monitoring", "Backup Power Systems", "Solar Maintenance",
    ]},
    {"id": "pools-spas-outdoor-living", "name": "Pools, Spas & Outdoor Living", "icon": "Waves", "color": "#0EA5E9", "subs": [
        "Swimming Pool Installation", "Spa Pool Installation", "Pool Pumps & Filtration",
        "Outdoor Kitchens", "Outdoor Lighting", "Shade Structures",
    ]},
    {"id": "insulation-weatherproofing", "name": "Insulation & Weatherproofing", "icon": "Thermometer", "color": "#65A30D", "subs": [
        "Ceiling Insulation", "Underfloor Insulation", "Wall Insulation",
        "Moisture Barriers", "Home Ventilation", "Weatherproofing",
    ]},
    {"id": "appliance-installation", "name": "Appliance Installation", "icon": "Refrigerator", "color": "#F59E0B", "subs": [
        "Ovens & Cooktops", "Dishwashers", "Rangehoods", "Washing Machines",
        "Dryers", "Waste Disposals", "Water Filters",
    ]},
    {"id": "specialist-home-services", "name": "Specialist Home Services", "icon": "HardHat", "color": "#DC2626", "subs": [
        "Waterproofing", "Asbestos Removal (Licensed)", "Demolition",
        "Structural Repairs", "Welding & Metal Fabrication", "Accessibility Modifications",
    ]},
]

COMMERCIAL_TAXONOMY = [
    {"id": "building-maintenance", "name": "Building Maintenance", "icon": "Building2", "color": "#3B82F6", "subs": [
        "General Building Maintenance", "Commercial Handyman", "Building Repairs",
        "Preventative Maintenance", "Building Alterations", "Minor Commercial Fit-outs",
    ]},
    {"id": "electrical", "name": "Electrical", "icon": "Zap", "color": "#F59E0B", "subs": [
        "Commercial Electrical", "Lighting Installation & Upgrades", "LED Retrofits",
        "Emergency Lighting", "Switchboard Upgrades", "Power & Data",
        "EV Charger Installation", "Electrical Fault Finding",
    ]},
    {"id": "plumbing-gas", "name": "Plumbing & Gas", "icon": "Droplets", "color": "#0EA5E9", "subs": [
        "Commercial Plumbing", "Drain Repairs", "Hot Water Systems", "Water Supply",
        "Pipework", "Bathrooms & Amenities", "Kitchens", "Gas Fitting",
    ]},
    {"id": "hvac-mechanical", "name": "HVAC & Mechanical", "icon": "Wind", "color": "#06B6D4", "subs": [
        "Commercial Air Conditioning", "Heat Pumps", "Ventilation Systems", "Refrigeration",
        "Extraction Systems", "HVAC Upgrades", "Mechanical Plant Installation",
    ]},
    {"id": "roofing-waterproofing", "name": "Roofing & Waterproofing", "icon": "Home", "color": "#EF4444", "subs": [
        "Roof Repairs", "Roof Replacement", "Commercial Roofing", "Gutters & Downpipes",
        "Membrane Roofing", "Waterproofing", "Leak Repairs",
    ]},
    {"id": "carpentry-joinery", "name": "Carpentry & Joinery", "icon": "Hammer", "color": "#A16207", "subs": [
        "Commercial Carpentry", "Office Fit-outs", "Doors & Hardware", "Windows",
        "Partitions", "Custom Joinery", "Cabinetry",
    ]},
    {"id": "interior-finishes", "name": "Interior Finishes", "icon": "Paintbrush", "color": "#EC4899", "subs": [
        "Painting", "Gib Installation", "Plastering", "Ceiling Repairs",
        "Suspended Ceilings", "Flooring", "Tiling",
    ]},
    {"id": "exterior-works", "name": "Exterior Works", "icon": "TreePine", "color": "#65A30D", "subs": [
        "Cladding", "Facade Repairs", "Concrete Repairs", "Asphalt",
        "Carparks", "Footpaths", "Retaining Walls", "Fencing & Gates",
    ]},
    {"id": "glass-aluminium", "name": "Glass & Aluminium", "icon": "Square", "color": "#0891B2", "subs": [
        "Commercial Glazing", "Shopfront Glass", "Aluminium Joinery",
        "Automatic Doors", "Glass Replacement", "Balustrades",
    ]},
    {"id": "fire-protection", "name": "Fire Protection", "icon": "Flame", "color": "#DC2626", "subs": [
        "Fire Alarms", "Fire Sprinklers", "Fire Doors", "Passive Fire Protection",
        "Fire Compliance Upgrades", "Emergency Lighting",
    ]},
    {"id": "security-systems", "name": "Security Systems", "icon": "ShieldCheck", "color": "#7C3AED", "subs": [
        "CCTV Installation", "Alarm Systems", "Access Control", "Intercom Systems",
        "Boom Gates", "Security Bollards", "Automatic Gates",
    ]},
    {"id": "data-communications", "name": "Data & Communications", "icon": "Router", "color": "#2563EB", "subs": [
        "Structured Cabling", "Fibre Installation", "Network Cabling",
        "Server Cabinets", "Wi-Fi Installation", "Communications Infrastructure",
    ]},
    {"id": "building-automation", "name": "Building Automation", "icon": "Cpu", "color": "#8B5CF6", "subs": [
        "Building Management Systems (BMS)", "Smart Lighting", "HVAC Controls",
        "Energy Monitoring", "Access Automation", "Smart Building Upgrades",
    ]},
    {"id": "renewable-energy", "name": "Renewable Energy", "icon": "Sun", "color": "#10B981", "subs": [
        "Commercial Solar", "Battery Storage", "EV Charging Infrastructure",
        "Energy Monitoring", "Solar Maintenance",
    ]},
    {"id": "renovations-fitouts", "name": "Commercial Renovations & Fit-outs", "icon": "Sparkles", "color": "#F97316", "subs": [
        "Office Renovations", "Retail Fit-outs", "Hospitality Fit-outs", "Medical Fit-outs",
        "Warehouse Fit-outs", "Interior Refurbishments", "Building Upgrades",
        "Accessibility Upgrades",
    ]},
]


def _slug(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _index_taxonomy(taxonomy: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for _cat in taxonomy:
        _cat_slug = _cat["id"]
        _sub_list = []
        for _sub in _cat["subs"]:
            _sub_id = _slug(_sub)
            _sub_list.append({"id": _sub_id, "name": _sub})
            idx[f"{_cat_slug}/{_sub_id}"] = {"category_id": _cat_slug, "category_name": _cat["name"], "sub_id": _sub_id, "sub_name": _sub}
        _cat["subcategories"] = _sub_list
    return idx


COMMERCIAL_TAXONOMY_INDEX = _index_taxonomy(COMMERCIAL_TAXONOMY)
RESIDENTIAL_TAXONOMY_INDEX = _index_taxonomy(RESIDENTIAL_TAXONOMY)


def _taxonomy_payload(taxonomy: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total_categories": len(taxonomy),
        "total_subcategories": sum(len(c["subs"]) for c in taxonomy),
        "categories": [
            {
                "id": c["id"],
                "name": c["name"],
                "icon": c["icon"],
                "color": c["color"],
                "subcategories": c["subcategories"],
            } for c in taxonomy
        ],
    }


@api.get("/services/commercial-taxonomy")
async def commercial_taxonomy():
    """15-category commercial services taxonomy with all subcategories."""
    return _taxonomy_payload(COMMERCIAL_TAXONOMY)


@api.get("/services/residential-taxonomy")
async def residential_taxonomy():
    """18-category residential home services taxonomy — homeowners, tenants, landlords, holiday-home owners."""
    return _taxonomy_payload(RESIDENTIAL_TAXONOMY)


@api.get("/services/taxonomy/{service_type}")
async def taxonomy_by_type(service_type: str):
    """Unified entry — pass 'residential' or 'commercial'."""
    if service_type == "commercial":
        return _taxonomy_payload(COMMERCIAL_TAXONOMY)
    if service_type == "residential":
        return _taxonomy_payload(RESIDENTIAL_TAXONOMY)
    raise HTTPException(status_code=404, detail="Unknown service_type. Use 'residential' or 'commercial'.")


@api.get("/services/commercial-taxonomy/{category_id}")
async def commercial_taxonomy_category(category_id: str):
    for c in COMMERCIAL_TAXONOMY:
        if c["id"] == category_id:
            return {"id": c["id"], "name": c["name"], "icon": c["icon"], "color": c["color"], "subcategories": c["subcategories"]}
    raise HTTPException(status_code=404, detail="Category not found")


@api.get("/services/residential-taxonomy/{category_id}")
async def residential_taxonomy_category(category_id: str):
    for c in RESIDENTIAL_TAXONOMY:
        if c["id"] == category_id:
            return {"id": c["id"], "name": c["name"], "icon": c["icon"], "color": c["color"], "subcategories": c["subcategories"]}
    raise HTTPException(status_code=404, detail="Category not found")


# ---------------- FORUM ----------------
FORUM_CATEGORIES = {
    "customer": [
        {"id": "maintenance", "name": "Home Maintenance", "icon": "Wrench", "color": "#3B82F6", "desc": "Preventive care, seasonal checklists, small fixes"},
        {"id": "renovations", "name": "Renovation Journeys", "icon": "Hammer", "color": "#EC4899", "desc": "Before/after, budgets, timelines, learnings"},
        {"id": "diy-vs-pro", "name": "DIY vs Hire a Pro", "icon": "HelpCircle", "color": "#8B5CF6", "desc": "When to DIY, when to call a tradie"},
        {"id": "reviews", "name": "Tradie Reviews", "icon": "Star", "color": "#F59E0B", "desc": "Share honest reviews of local pros"},
        {"id": "cost-questions", "name": "Cost Questions", "icon": "DollarSign", "color": "#10B981", "desc": "Is this quote fair? Compare pricing with neighbours"},
        {"id": "smart-home", "name": "Smart Home & Efficiency", "icon": "Home", "color": "#06B6D4", "desc": "Heat pumps, insulation, solar, EV chargers"},
        {"id": "landlord-corner", "name": "Landlord Corner", "icon": "KeyRound", "color": "#F97316", "desc": "Rental compliance, Healthy Homes, tenant care"},
        {"id": "disputes", "name": "Dispute Advice", "icon": "Gavel", "color": "#EF4444", "desc": "Warranty, workmanship, DBH complaints"},
    ],
    "provider": [
        {"id": "pricing", "name": "Pricing & Quoting", "icon": "DollarSign", "color": "#10B981", "desc": "Rate cards, markups, call-out fees, quote strategy"},
        {"id": "reno-projects", "name": "Renovation Projects", "icon": "Hammer", "color": "#EC4899", "desc": "Bathroom, kitchen, extensions — case studies & tips"},
        {"id": "maintenance-ops", "name": "Maintenance Ops", "icon": "Wrench", "color": "#3B82F6", "desc": "Route planning, preventive schedules, callback rates"},
        {"id": "compliance", "name": "Compliance & Building Code", "icon": "ShieldCheck", "color": "#EF4444", "desc": "H&S, licensing, insurance, NZBC, Healthy Homes"},
        {"id": "suppliers", "name": "Suppliers & Wholesalers", "icon": "Truck", "color": "#F59E0B", "desc": "Bunnings vs Mitre 10 vs trade merchants"},
        {"id": "tools-materials", "name": "Tools & Materials", "icon": "HardHat", "color": "#6B7280", "desc": "Product reviews, best-value gear"},
        {"id": "business", "name": "Business Ops", "icon": "Briefcase", "color": "#8B5CF6", "desc": "Hiring apprentices, GST, software, invoicing"},
        {"id": "market-trends", "name": "Market Trends", "icon": "TrendingUp", "color": "#0EA5E9", "desc": "What's hot in NZ — demand, lead flow, forecasts"},
        {"id": "smoko-room", "name": "The Smoko Room", "icon": "Coffee", "color": "#78716C", "desc": "Banter, memes, weekend chat"},
    ],
}


class ForumPostCreate(BaseModel):
    title: str
    body: str
    category: str
    tags: List[str] = []


class ForumReplyCreate(BaseModel):
    body: str
    parent_reply_id: Optional[str] = None


def _forum_audience(role: str) -> str:
    return "provider" if role == "provider" else "customer"


def _hot_score(post: Dict[str, Any]) -> float:
    """Reddit-style hot ranking."""
    score = (post.get("upvotes", 0) - post.get("downvotes", 0))
    order = (abs(score) if score != 0 else 1)
    import math
    order = math.log10(max(order, 1))
    sign = 1 if score > 0 else (-1 if score < 0 else 0)
    created = post.get("created_at")
    if isinstance(created, datetime):
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        seconds = (created - datetime(2026, 1, 1, tzinfo=timezone.utc)).total_seconds()
    else:
        seconds = 0
    return round(sign * order + seconds / 45000, 7)


def _serialize_post(post: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    p = {k: v for k, v in post.items() if k != "_id"}
    p["score"] = post.get("upvotes", 0) - post.get("downvotes", 0)
    p["user_vote"] = 0
    if user_id and post.get("voters"):
        for v in post["voters"]:
            if v.get("user_id") == user_id:
                p["user_vote"] = v.get("value", 0)
                break
    p.pop("voters", None)
    p.pop("viewers", None)
    return p


@api.get("/forum/categories")
async def forum_categories(user=Depends(require_user)):
    audience = _forum_audience(user["role"])
    return {"audience": audience, "categories": FORUM_CATEGORIES[audience]}


@api.get("/forum/posts")
async def list_forum_posts(
    category: Optional[str] = None,
    sort: str = "hot",
    q: Optional[str] = None,
    user=Depends(require_user),
):
    audience = _forum_audience(user["role"])
    query: Dict[str, Any] = {"audience": audience}
    if category and category != "all":
        query["category"] = category
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"body": {"$regex": q, "$options": "i"}},
        ]
    cursor = db.forum_posts.find(query)
    if sort == "new":
        cursor = cursor.sort("created_at", -1)
    elif sort == "top":
        cursor = cursor.sort([("upvotes", -1), ("created_at", -1)])
    else:  # hot
        cursor = cursor.sort([("hot_score", -1), ("created_at", -1)])
    posts = await cursor.limit(100).to_list(100)
    return [_serialize_post(p, user["user_id"]) for p in posts]


@api.get("/forum/posts/{post_id}")
async def get_forum_post(post_id: str, user=Depends(require_user)):
    post = await db.forum_posts.find_one({"post_id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    audience = _forum_audience(user["role"])
    if post.get("audience") != audience:
        raise HTTPException(status_code=403, detail="Not visible in your community")
    # Unique-viewer tracking — increment views ONCE per user (author excluded)
    uid = user["user_id"]
    if uid != post.get("author_id") and uid not in (post.get("viewers") or []):
        await db.forum_posts.update_one(
            {"post_id": post_id},
            {"$inc": {"views": 1}, "$addToSet": {"viewers": uid}},
        )
        post["views"] = post.get("views", 0) + 1
    replies = await db.forum_replies.find({"post_id": post_id}).sort("created_at", 1).to_list(500)
    return {
        "post": _serialize_post(post, uid),
        "replies": [_serialize_reply(r, uid) for r in replies],
    }


def _serialize_reply(reply: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    r = {k: v for k, v in reply.items() if k != "_id"}
    r["score"] = reply.get("upvotes", 0) - reply.get("downvotes", 0)
    r["user_vote"] = 0
    if user_id and reply.get("voters"):
        for v in reply["voters"]:
            if v.get("user_id") == user_id:
                r["user_vote"] = v.get("value", 0)
                break
    r.pop("voters", None)
    return r


@api.post("/forum/posts")
async def create_forum_post(payload: ForumPostCreate, user=Depends(require_user)):
    audience = _forum_audience(user["role"])
    valid_cats = {c["id"] for c in FORUM_CATEGORIES[audience]}
    if payload.category not in valid_cats:
        raise HTTPException(status_code=400, detail="Invalid category for your community")
    if len(payload.title.strip()) < 5:
        raise HTTPException(status_code=400, detail="Title too short (min 5 chars)")
    if len(payload.body.strip()) < 10:
        raise HTTPException(status_code=400, detail="Body too short (min 10 chars)")
    now = datetime.now(timezone.utc)
    post = {
        "post_id": f"fp_{uuid.uuid4().hex[:12]}",
        "audience": audience,
        "category": payload.category,
        "title": payload.title.strip(),
        "body": payload.body.strip(),
        "tags": [t.strip().lower() for t in payload.tags if t.strip()][:5],
        "author_id": user["user_id"],
        "author_name": user["name"],
        "author_role": user["role"],
        "upvotes": 1,
        "downvotes": 0,
        "voters": [{"user_id": user["user_id"], "value": 1}],
        "replies_count": 0,
        "views": 0,
        "pinned": False,
        "created_at": now,
        "updated_at": now,
        "hot_score": 0.0,
    }
    post["hot_score"] = _hot_score(post)
    await db.forum_posts.insert_one(post)
    return _serialize_post(post, user["user_id"])


@api.post("/forum/posts/{post_id}/replies")
async def create_forum_reply(post_id: str, payload: ForumReplyCreate, user=Depends(require_user)):
    post = await db.forum_posts.find_one({"post_id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    audience = _forum_audience(user["role"])
    if post.get("audience") != audience:
        raise HTTPException(status_code=403, detail="Not visible in your community")
    if len(payload.body.strip()) < 2:
        raise HTTPException(status_code=400, detail="Reply too short")
    now = datetime.now(timezone.utc)
    reply = {
        "reply_id": f"fr_{uuid.uuid4().hex[:12]}",
        "post_id": post_id,
        "parent_reply_id": payload.parent_reply_id,
        "author_id": user["user_id"],
        "author_name": user["name"],
        "author_role": user["role"],
        "body": payload.body.strip(),
        "upvotes": 1,
        "downvotes": 0,
        "voters": [{"user_id": user["user_id"], "value": 1}],
        "created_at": now,
    }
    await db.forum_replies.insert_one(reply)
    await db.forum_posts.update_one(
        {"post_id": post_id},
        {"$inc": {"replies_count": 1}, "$set": {"updated_at": now}},
    )
    return _serialize_reply(reply, user["user_id"])


async def _vote(coll_name: str, id_field: str, target_id: str, value: int, user_id: str) -> Dict[str, Any]:
    if value not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="Vote must be -1, 0 or 1")
    coll = db[coll_name]
    doc = await coll.find_one({id_field: target_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    voters = doc.get("voters", [])
    existing = next((v for v in voters if v.get("user_id") == user_id), None)
    up = doc.get("upvotes", 0)
    down = doc.get("downvotes", 0)
    if existing:
        prev = existing.get("value", 0)
        if prev == 1:
            up -= 1
        if prev == -1:
            down -= 1
        voters = [v for v in voters if v.get("user_id") != user_id]
    if value == 1:
        up += 1
    if value == -1:
        down += 1
    if value != 0:
        voters.append({"user_id": user_id, "value": value})
    update = {"upvotes": max(0, up), "downvotes": max(0, down), "voters": voters}
    if coll_name == "forum_posts":
        merged = {**doc, **update}
        update["hot_score"] = _hot_score(merged)
    await coll.update_one({id_field: target_id}, {"$set": update})
    return {"score": update["upvotes"] - update["downvotes"], "user_vote": value, "upvotes": update["upvotes"], "downvotes": update["downvotes"]}


@api.post("/forum/posts/{post_id}/vote")
async def vote_forum_post(post_id: str, body: Dict[str, Any], user=Depends(require_user)):
    return await _vote("forum_posts", "post_id", post_id, int(body.get("value", 0)), user["user_id"])


@api.post("/forum/replies/{reply_id}/vote")
async def vote_forum_reply(reply_id: str, body: Dict[str, Any], user=Depends(require_user)):
    return await _vote("forum_replies", "reply_id", reply_id, int(body.get("value", 0)), user["user_id"])


@api.delete("/forum/posts/{post_id}")
async def delete_forum_post(post_id: str, user=Depends(require_user)):
    post = await db.forum_posts.find_one({"post_id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("author_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")
    await db.forum_posts.delete_one({"post_id": post_id})
    await db.forum_replies.delete_many({"post_id": post_id})
    return {"ok": True}


@api.get("/forum/stats")
async def forum_stats(user=Depends(require_user)):
    audience = _forum_audience(user["role"])
    posts = await db.forum_posts.count_documents({"audience": audience})
    replies_agg = await db.forum_replies.aggregate([
        {"$lookup": {"from": "forum_posts", "localField": "post_id", "foreignField": "post_id", "as": "p"}},
        {"$match": {"p.audience": audience}},
        {"$count": "n"},
    ]).to_list(1)
    replies = replies_agg[0]["n"] if replies_agg else 0
    members = await db.users.count_documents({"role": "provider" if audience == "provider" else {"$in": ["customer", "property", "landlord", "facilities", "insurance"]}})
    online = await db.forum_posts.count_documents({"audience": audience, "updated_at": {"$gt": datetime.now(timezone.utc) - timedelta(hours=24)}})
    return {"audience": audience, "posts": posts, "replies": replies, "members": members, "active_today": online}


# ---------------- COST GUIDE ----------------
COST_GUIDE = [
    {"category": "Plumbing", "job": "Leaking tap repair", "low": 80, "high": 180, "avg": 120, "unit": "job"},
    {"category": "Plumbing", "job": "Toilet install", "low": 250, "high": 450, "avg": 320, "unit": "job"},
    {"category": "Plumbing", "job": "Hot water cylinder replacement", "low": 1200, "high": 2400, "avg": 1650, "unit": "job"},
    {"category": "Electrical", "job": "Power point install", "low": 120, "high": 220, "avg": 160, "unit": "each"},
    {"category": "Electrical", "job": "Full house rewire", "low": 8000, "high": 15000, "avg": 11500, "unit": "job"},
    {"category": "Electrical", "job": "LED downlights (per light)", "low": 45, "high": 90, "avg": 65, "unit": "each"},
    {"category": "Heat Pump", "job": "3.2kW heat pump install", "low": 2200, "high": 3200, "avg": 2650, "unit": "unit"},
    {"category": "Painting", "job": "Interior painting per room", "low": 400, "high": 900, "avg": 600, "unit": "room"},
    {"category": "Cleaning", "job": "Standard house clean", "low": 90, "high": 180, "avg": 130, "unit": "visit"},
    {"category": "Cleaning", "job": "Deep clean / bond", "low": 350, "high": 700, "avg": 480, "unit": "job"},
    {"category": "Lawn & Garden", "job": "Lawn mow (residential)", "low": 45, "high": 90, "avg": 65, "unit": "visit"},
    {"category": "Handyman", "job": "General repairs (per hour)", "low": 65, "high": 95, "avg": 80, "unit": "hour"},
    {"category": "Roofing", "job": "Roof repair (leak)", "low": 350, "high": 900, "avg": 580, "unit": "job"},
    {"category": "Bathroom", "job": "Full bathroom renovation", "low": 12000, "high": 25000, "avg": 18500, "unit": "job"},
    {"category": "Kitchen", "job": "Kitchen renovation", "low": 15000, "high": 40000, "avg": 25000, "unit": "job"},
]


@api.get("/cost-guide")
async def cost_guide(category: Optional[str] = None):
    if category:
        return [c for c in COST_GUIDE if c["category"].lower() == category.lower()]
    return COST_GUIDE


# ---------------- CATEGORIES ----------------
CATEGORIES = [
    {"id": "plumbing", "name": "Plumbing", "icon": "Wrench", "color": "#3B82F6"},
    {"id": "electrical", "name": "Electrical", "icon": "Zap", "color": "#F59E0B"},
    {"id": "cleaning", "name": "Cleaning", "icon": "Sparkles", "color": "#10B981"},
    {"id": "lawn", "name": "Lawn & Garden", "icon": "Trees", "color": "#22C55E"},
    {"id": "hvac", "name": "Heat Pump / HVAC", "icon": "Wind", "color": "#06B6D4"},
    {"id": "handyman", "name": "Handyman", "icon": "Hammer", "color": "#8B5CF6"},
    {"id": "painting", "name": "Painting", "icon": "Paintbrush", "color": "#EC4899"},
    {"id": "roofing", "name": "Roofing", "icon": "Home", "color": "#F97316"},
    {"id": "renovation", "name": "Renovation", "icon": "Hammer", "color": "#6366F1"},
    {"id": "appliance", "name": "Appliance Repair", "icon": "Refrigerator", "color": "#0EA5E9"},
    {"id": "moving", "name": "Moving", "icon": "Truck", "color": "#EF4444"},
    {"id": "pest", "name": "Pest Control", "icon": "Bug", "color": "#84CC16"},
]


@api.get("/categories")
async def get_categories():
    return CATEGORIES


@api.get("/")
async def root():
    return {"message": "Pro Finder NZ API", "version": "1.0"}


# ---------------- SEED DATA ----------------
async def seed_data():
    """Seed products, sample providers, feed posts if empty."""
    # PRODUCTS - refresh if we don't have the Trade Supply Co. style products
    if await db.products.count_documents({"unit": {"$exists": True}}) == 0:
        await db.products.delete_many({})
        products = [
            # ---- POWER TOOLS ----
            {"product_id": "ts001", "name": "Makita 18V LXT Combi Drill Kit", "category": "Power Tools", "price": 349.0, "original_price": 429.0, "discount": 19, "unit": "kit", "featured": True, "trade_only": True, "image": "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=600&auto=format", "brand": "Makita", "description": "18V brushless combi drill with 2x 5Ah batteries, charger, and carry case. 80Nm torque, 13mm chuck.", "in_stock": True, "rating": 4.9, "reviews_count": 512},
            {"product_id": "ts002", "name": "DeWalt 54V FLEXVOLT Circular Saw", "category": "Power Tools", "price": 549.0, "original_price": 649.0, "discount": 15, "unit": "each", "featured": True, "trade_only": True, "image": "https://images.unsplash.com/photo-1581092160562-40aa08e78837?w=600&auto=format", "brand": "DeWalt", "description": "54V XR FLEXVOLT 190mm circular saw. Cuts 67mm at 90°, 47mm at 45°. Includes 24T TCT blade.", "in_stock": True, "rating": 4.7, "reviews_count": 88},
            {"product_id": "ts003", "name": "Milwaukee M18 Fuel Impact Driver", "category": "Power Tools", "price": 449.0, "original_price": 529.0, "discount": 15, "unit": "kit", "trade_only": True, "image": "https://images.unsplash.com/photo-1572981779307-38e8b9d2d1f6?w=600&auto=format", "brand": "Milwaukee", "description": "M18 Fuel brushless impact driver, 226Nm, 3-mode control.", "in_stock": True, "rating": 4.8, "reviews_count": 214},
            {"product_id": "ts004", "name": "Bosch GBH 2-26 Rotary Hammer", "category": "Power Tools", "price": 329.0, "original_price": 389.0, "discount": 15, "unit": "each", "trade_only": True, "image": "https://images.unsplash.com/photo-1530124566582-a618bc2615dc?w=600&auto=format", "brand": "Bosch", "description": "830W SDS-Plus rotary hammer, 2.7J impact energy.", "in_stock": True, "rating": 4.6, "reviews_count": 76},
            # ---- HAND TOOLS ----
            {"product_id": "ts005", "name": "Stanley FatMax 8m Tape Measure", "category": "Hand Tools", "price": 39.0, "unit": "each", "trade_only": False, "image": "https://images.unsplash.com/photo-1591958911259-bee2173bdccc?w=600&auto=format", "brand": "Stanley", "description": "Heavy-duty 8m tape with FatMax blade armour.", "in_stock": True, "rating": 4.7, "reviews_count": 340},
            {"product_id": "ts006", "name": "Estwing 20oz Framing Hammer", "category": "Hand Tools", "price": 89.0, "unit": "each", "trade_only": False, "image": "https://images.unsplash.com/photo-1502741224143-90386d7f8c82?w=600&auto=format", "brand": "Estwing", "description": "Solid steel hammer with leather grip. Made in USA.", "in_stock": True, "rating": 4.9, "reviews_count": 187},
            {"product_id": "ts007", "name": "Knipex Cobra Pliers 250mm", "category": "Hand Tools", "price": 79.0, "unit": "each", "trade_only": True, "image": "https://images.unsplash.com/photo-1607472586893-edb57bdc0e39?w=600&auto=format", "brand": "Knipex", "description": "Self-gripping water pump pliers. Made in Germany.", "in_stock": True, "rating": 4.8, "reviews_count": 122},
            # ---- EQUIPMENT ----
            {"product_id": "ts008", "name": "Atlas Copco LT6D 240V Air Compressor 24L", "category": "Equipment", "price": 549.0, "original_price": 649.0, "discount": 15, "unit": "each", "featured": True, "trade_only": True, "image": "https://images.unsplash.com/photo-1631545308456-c1eb1c1d0c0f?w=600&auto=format", "brand": "Atlas Copco", "description": "24L direct-drive air compressor. 2HP motor, 116 PSI, 180L/min FAD. Ideal for framing.", "in_stock": True, "rating": 4.6, "reviews_count": 54},
            {"product_id": "ts009", "name": "Honda EU22i Inverter Generator 2.2kW", "category": "Equipment", "price": 1699.0, "unit": "each", "featured": True, "trade_only": True, "image": "https://images.unsplash.com/photo-1605281317010-fe5ffe798166?w=600&auto=format", "brand": "Honda", "description": "2.2kW inverter generator. Eco-Throttle, ultra-quiet 53dB. Parallel capability. 7hr runtime.", "in_stock": True, "rating": 4.9, "reviews_count": 96},
            {"product_id": "ts010", "name": "Karcher HD 5/12C Pressure Washer", "category": "Equipment", "price": 1149.0, "original_price": 1349.0, "discount": 15, "unit": "each", "trade_only": True, "image": "https://images.unsplash.com/photo-1558959357-4c7ffbec8b34?w=600&auto=format", "brand": "Karcher", "description": "Professional 170bar cold water pressure washer.", "in_stock": True, "rating": 4.7, "reviews_count": 42},
            # ---- FIXINGS ----
            {"product_id": "ts011", "name": "Buildex 14g x 100mm Timber Screws (500pk)", "category": "Fixings", "price": 69.0, "unit": "500pk", "trade_only": True, "image": "https://images.unsplash.com/photo-1609205807107-e8ec2120f9de?w=600&auto=format", "brand": "Buildex", "description": "Type 17 self-drilling timber screws, ClimaCoat.", "in_stock": True, "rating": 4.7, "reviews_count": 89},
            {"product_id": "ts012", "name": "Ramset DynaBolt Plus 12x100 (10pk)", "category": "Fixings", "price": 45.0, "unit": "10pk", "trade_only": True, "image": "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=600&auto=format", "brand": "Ramset", "description": "Sleeve anchor for concrete, 12x100mm.", "in_stock": True, "rating": 4.6, "reviews_count": 55},
            # ---- MATERIALS ----
            {"product_id": "ts013", "name": "Pink Batts R2.6 Ceiling Insulation 4.8m² Bag", "category": "Materials", "price": 58.0, "unit": "bag", "featured": True, "trade_only": True, "image": "https://images.unsplash.com/photo-1591016749860-9cb6015d3596?w=600&auto=format", "brand": "Pink Batts", "description": "R2.6 glasswool ceiling insulation. 4.8m² per bag. 580mm wide batts. HHS compliant for ceilings.", "in_stock": True, "rating": 4.8, "reviews_count": 176},
            {"product_id": "ts014", "name": "Gib Plasterboard 10mm 2400x1200", "category": "Materials", "price": 39.0, "unit": "sheet", "trade_only": True, "image": "https://images.unsplash.com/photo-1590725175577-5e6c2f7bd67d?w=600&auto=format", "brand": "GIB", "description": "Standard 10mm plasterboard sheet, 2.88m².", "in_stock": True, "rating": 4.7, "reviews_count": 210},
            {"product_id": "ts015", "name": "Golden Bay Concrete 20kg Bag", "category": "Materials", "price": 12.0, "unit": "bag", "image": "https://images.unsplash.com/photo-1587582423116-ec07293f0bd4?w=600&auto=format", "brand": "Golden Bay", "description": "20kg dry-mix concrete, general purpose 25MPa.", "in_stock": True, "rating": 4.6, "reviews_count": 88},
            # ---- PLUMBING ----
            {"product_id": "ts016", "name": "Dux 180L Electric Hot Water Cylinder", "category": "Plumbing", "price": 1299.0, "original_price": 1499.0, "discount": 13, "unit": "each", "featured": True, "trade_only": True, "image": "https://images.unsplash.com/photo-1620626011761-996317b8d101?w=600&auto=format", "brand": "Dux", "description": "180L low-pressure electric storage cylinder. 2.4kW element, thermostat 60–75°C. Vitreous enamel lining. 10yr warranty.", "in_stock": True, "rating": 4.7, "reviews_count": 74},
            {"product_id": "ts017", "name": "Methven Aio Chrome Basin Mixer", "category": "Plumbing", "price": 289.0, "unit": "each", "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&auto=format", "brand": "Methven", "description": "Aurajet basin mixer with chrome finish. 15yr warranty.", "in_stock": True, "rating": 4.8, "reviews_count": 143},
            {"product_id": "ts018", "name": "Rehau Rautitan PEXa Pipe 20mm x 50m", "category": "Plumbing", "price": 189.0, "unit": "roll", "trade_only": True, "image": "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=600&auto=format", "brand": "Rehau", "description": "Cross-linked polyethylene pipe for hot & cold plumbing.", "in_stock": True, "rating": 4.7, "reviews_count": 47},
            # ---- ELECTRICAL ----
            {"product_id": "ts019", "name": "Thorn LED Downlight 9W 3000K Warm White (10pk)", "category": "Electrical", "price": 129.0, "original_price": 159.0, "discount": 19, "unit": "10pk", "featured": True, "trade_only": True, "image": "https://images.unsplash.com/photo-1524661135-423995f22d0b?w=600&auto=format", "brand": "Thorn", "description": "9W LED downlight 3000K warm white. 720lm, 90mm cutout, IP44 rated. Dimmable.", "in_stock": True, "rating": 4.8, "reviews_count": 342},
            {"product_id": "ts020", "name": "PDL Iconic 4-Gang Powerpoint White", "category": "Electrical", "price": 89.0, "unit": "each", "trade_only": False, "image": "https://images.unsplash.com/photo-1518005020951-eccb494ad742?w=600&auto=format", "brand": "PDL", "description": "4-gang double switched socket, white.", "in_stock": True, "rating": 4.7, "reviews_count": 89},
            {"product_id": "ts021", "name": "Olex 2.5mm² TPS Electrical Cable 100m", "category": "Electrical", "price": 219.0, "unit": "roll", "trade_only": True, "image": "https://images.unsplash.com/photo-1517495306984-f84210f9daa8?w=600&auto=format", "brand": "Olex", "description": "2.5mm² TPS twin+earth building wire, 100m drum.", "in_stock": True, "rating": 4.7, "reviews_count": 61},
            # ---- KITSETS ----
            {"product_id": "ts022", "name": "Caroma 600mm Wall Hung Vanity Kitset", "category": "Kitsets", "price": 649.0, "original_price": 799.0, "discount": 19, "unit": "kitset", "featured": True, "image": "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=600&auto=format", "brand": "Caroma", "description": "600mm wall-hung floating vanity with integrated basin, mirror and tap hole. White gloss.", "in_stock": True, "rating": 4.7, "reviews_count": 41},
            {"product_id": "ts023", "name": "GardenMaster 3x3m Steel Shed Kitset", "category": "Kitsets", "price": 1899.0, "original_price": 2299.0, "discount": 17, "unit": "kitset", "image": "https://images.unsplash.com/photo-1602103928956-a19dc37d1e30?w=600&auto=format", "brand": "GardenMaster", "description": "Full DIY steel shed kitset with concrete anchors, timber floor plate ready.", "in_stock": True, "rating": 4.4, "reviews_count": 35},
            {"product_id": "ts024", "name": "Complete Ensuite Renovation Kit", "category": "Kitsets", "price": 3999.0, "original_price": 4799.0, "discount": 17, "unit": "kitset", "image": "https://images.unsplash.com/photo-1620626011761-996317b8d101?w=600&auto=format", "brand": "Bathroom Co", "description": "Vanity, WC, mixer, shower and tiles in one bundle.", "in_stock": True, "rating": 4.6, "reviews_count": 22},
            # ---- SAFETY & PPE ----
            {"product_id": "ts025", "name": "3M Safety Boots Steel Cap Size 10", "category": "Safety & PPE", "price": 189.0, "unit": "pair", "featured": True, "image": "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=600&auto=format", "brand": "3M", "description": "Steel toe cap safety boots. Certified AS/NZS 2210.", "in_stock": True, "rating": 4.7, "reviews_count": 132},
            {"product_id": "ts026", "name": "Hi-Vis Polo Shirt with Reflective (Orange)", "category": "Safety & PPE", "price": 39.0, "unit": "each", "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&auto=format", "brand": "Bison", "description": "Day/night hi-vis polo shirt, reflective tape.", "in_stock": True, "rating": 4.6, "reviews_count": 88},
            {"product_id": "ts027", "name": "3M P2 Disposable Respirator (20pk)", "category": "Safety & PPE", "price": 45.0, "unit": "20pk", "image": "https://images.unsplash.com/photo-1584634731339-252c581abfc5?w=600&auto=format", "brand": "3M", "description": "Cup-shaped P2 particulate respirator with valve.", "in_stock": True, "rating": 4.8, "reviews_count": 189},
            # ---- HEATING & COOLING (kept for marketplace tab) ----
            {"product_id": "p001", "name": "Mitsubishi 5kW Inverter Heat Pump", "category": "Heating & Cooling", "price": 2499.0, "original_price": 2899.0, "discount": 14, "unit": "unit", "image": "https://images.unsplash.com/photo-1631545308456-c1eb1c1d0c0f?w=600&auto=format", "brand": "Mitsubishi", "description": "Energy efficient inverter heat pump, ideal for medium rooms.", "in_stock": True, "rating": 4.7, "reviews_count": 128},
            {"product_id": "p002", "name": "Daikin 7kW Premium Heat Pump", "category": "Heating & Cooling", "price": 3299.0, "original_price": 3799.0, "discount": 13, "unit": "unit", "image": "https://images.unsplash.com/photo-1585129777188-95d16bec91b9?w=600&auto=format", "brand": "Daikin", "description": "Whisper quiet, ideal for large open plan living.", "in_stock": True, "rating": 4.8, "reviews_count": 92},
        ]
        await db.products.insert_many(products)

    # DEMO PROVIDERS with locations (only if none exist)
    if await db.provider_profiles.count_documents({}) == 0:
        demo_providers = [
            {"name": "Sarah Chen Plumbing", "email": "sarah@dispatchr.demo", "cats": ["plumbing"], "lat": -36.8485, "lng": 174.7633, "rate": 95.0, "rating": 4.9, "reviews": 187, "jobs": 320},
            {"name": "MP Electrical", "email": "mp@dispatchr.demo", "cats": ["electrical"], "lat": -36.8585, "lng": 174.7833, "rate": 85.0, "rating": 4.7, "reviews": 142, "jobs": 210},
            {"name": "CoolAir Solutions", "email": "coolair@dispatchr.demo", "cats": ["hvac"], "lat": -36.8385, "lng": 174.7433, "rate": 90.0, "rating": 4.8, "reviews": 98, "jobs": 156},
            {"name": "GreenLawn Care", "email": "green@dispatchr.demo", "cats": ["lawn"], "lat": -36.8285, "lng": 174.7233, "rate": 55.0, "rating": 4.6, "reviews": 76, "jobs": 189},
            {"name": "SparkClean Services", "email": "sparkclean@dispatchr.demo", "cats": ["cleaning"], "lat": -36.8685, "lng": 174.7933, "rate": 45.0, "rating": 4.8, "reviews": 245, "jobs": 412},
            {"name": "Home Automation Pro", "email": "auto@dispatchr.demo", "cats": ["handyman", "electrical"], "lat": -36.8485, "lng": 174.7433, "rate": 100.0, "rating": 4.9, "reviews": 62, "jobs": 88},
            {"name": "Rapid Repairs", "email": "rapid@dispatchr.demo", "cats": ["handyman"], "lat": -36.8585, "lng": 174.7533, "rate": 75.0, "rating": 4.7, "reviews": 134, "jobs": 218},
            {"name": "PainterPro NZ", "email": "painterpro@dispatchr.demo", "cats": ["painting"], "lat": -36.8785, "lng": 174.7033, "rate": 65.0, "rating": 4.6, "reviews": 89, "jobs": 145},
            {"name": "Roofline Experts", "email": "roofline@dispatchr.demo", "cats": ["roofing"], "lat": -36.8185, "lng": 174.7833, "rate": 110.0, "rating": 4.8, "reviews": 54, "jobs": 92},
        ]
        # Rich provider gallery + review templates for the directory browse UI
        _stock_gallery = [
            "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800&q=80",
            "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=800&q=80",
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=800&q=80",
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80",
            "https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?w=800&q=80",
        ]
        _review_templates = [
            {"rating": 5, "text": "Punctual, tidy, and thorough. Job was done in half the time I expected.", "author": "Emma T."},
            {"rating": 5, "text": "Best trade I've hired on Pro Finder NZ. Fair price and cleaned up after themselves.", "author": "Jack R."},
            {"rating": 4, "text": "Good work. Quote came in a bit higher than others but quality was worth it.", "author": "Priya S."},
            {"rating": 5, "text": "Called at 8pm on a Sunday, showed up at 9am Monday. Life savers.", "author": "Ben M."},
            {"rating": 4, "text": "Solid. Communication could be a bit faster but the workmanship is spot on.", "author": "Anna K."},
        ]
        for p in demo_providers:
            uid = f"user_{uuid.uuid4().hex[:12]}"
            await db.users.insert_one({
                "user_id": uid,
                "email": p["email"],
                "name": p["name"],
                "role": "provider",
                "picture": None,
                "city": "Auckland",
                "created_at": datetime.now(timezone.utc),
                "password_hash": hash_password("demo1234"),
            })
            await db.provider_profiles.insert_one({
                "user_id": uid,
                "business_name": p["name"],
                "categories": p["cats"],
                "subcategories": p.get("subs", []),
                "hourly_rate": p["rate"],
                "rating": p["rating"],
                "reviews_count": p["reviews"],
                "jobs_completed": p["jobs"],
                "verified": True,
                "insured": True,
                "background_checked": p["reviews"] > 30,
                "accredited": p["reviews"] > 50,
                "response_time_hours": 2 if p["reviews"] > 100 else 6,
                "years_in_business": max(3, p["jobs"] // 40),
                "gallery": _stock_gallery[:4],
                "plan": "pro",
                "latitude": p["lat"],
                "longitude": p["lng"],
                "online": True,
                "bio": f"Trusted {p['cats'][0]} professional in Auckland with {p['jobs']}+ completed jobs. Fully insured, licensed, and background-checked. Available 7 days a week for {p['cats'][0]} repairs, installations, and maintenance.",
            })
            # Seed 3 reviews per provider
            for i, tmpl in enumerate(_review_templates[:3]):
                await db.provider_reviews.insert_one({
                    "review_id": f"rev_{uuid.uuid4().hex[:10]}",
                    "provider_id": uid,
                    "author_name": tmpl["author"],
                    "rating": tmpl["rating"],
                    "text": tmpl["text"],
                    "created_at": datetime.now(timezone.utc) - timedelta(days=i * 14 + 3),
                })

    # FEED POSTS
    if await db.feed_posts.count_documents({}) == 0:
        providers = await db.provider_profiles.find({}, {"_id": 0}).to_list(50)
        if providers:
            sample_posts = [
                {"post_type": "sale", "title": "Summer Special: 20% Off All Deck Repairs!",
                 "content": "Getting your deck ready for summer BBQs? We're offering 20% off all deck repairs and staining services booked this month. Our team uses premium weather-resistant stains that last 5+ years. Limited slots available - book now before the rush!\n\n- Free quotes within 24 hours\n- Fully insured & licensed\n- 3-year workmanship guarantee",
                 "tags": ["decks", "summer", "discount", "auckland"], "likes": 47, "comments_count": 12},
                {"post_type": "sale", "title": "Heat Pump Installation Sale - $500 Off Fujitsu Units",
                 "content": "Winter is coming! Get ahead of the cold with our Fujitsu heat pump installation special:\n\nFujitsu 3.2kW Hi-Wall - $2,499 installed (was $2,999)\nFujitsu 5.0kW Hi-Wall - $3,199 installed (was $3,699)\nFujitsu 8.0kW Hi-Wall - $4,499 installed (was $4,999)\n\nAll units come with:\n• 6-year manufacturer warranty\n• Professional installation by certified technicians",
                 "tags": ["heatpumps", "sale", "winter"], "likes": 89, "comments_count": 23},
                {"post_type": "article", "title": "5 Signs You Need a New Hot Water Cylinder",
                 "content": "Is your hot water running out too quickly? Here are five telltale signs you should replace your cylinder before it fails: 1) Age over 10 years, 2) Rusty water, 3) Frequent pressure drops, 4) Visible leaks, 5) Strange noises. Book a free inspection with us today.",
                 "tags": ["plumbing", "tips"], "likes": 34, "comments_count": 5},
                {"post_type": "news", "title": "New Emergency Response Team Launched",
                 "content": "Our new emergency dispatch team is now available 24/7 for burst pipes, electrical faults and roof leaks. Response guaranteed within 60 minutes across Auckland.",
                 "tags": ["news", "emergency"], "likes": 62, "comments_count": 18},
                {"post_type": "update", "title": "Bathroom Reno Complete in Ponsonby",
                 "content": "Another beautiful bathroom renovation completed in Ponsonby! Full re-tile, new vanity and shower - 6 days start to finish. Book your consultation today.",
                 "tags": ["renovation", "bathroom"], "likes": 128, "comments_count": 34},
                {"post_type": "report", "title": "Property Maintenance Report - Q1 2026",
                 "content": "Our quarterly report shows a 12% increase in preventive maintenance bookings. Winter prep, gutter cleaning and heat pump servicing lead the demand.",
                 "tags": ["report", "insights"], "likes": 22, "comments_count": 3},
            ]
            for i, sp in enumerate(sample_posts):
                pr = providers[i % len(providers)]
                await db.feed_posts.insert_one({
                    "post_id": f"pst_{uuid.uuid4().hex[:10]}",
                    "author_id": pr["user_id"],
                    "author_name": pr["business_name"],
                    "author_type": "provider",
                    "author_category": (pr.get("categories") or ["General"])[0],
                    "author_verified": True,
                    "liked_by": [],
                    "created_at": datetime.now(timezone.utc) - timedelta(days=i * 3),
                    **sp,
                })

    # EXTERNAL JOBS (partner leads)
    if await db.external_jobs.count_documents({}) == 0:
        externals = [
            {"source": "Builderscrack", "title": "Kitchen renovation - Mt Eden", "category": "renovation", "budget": "$25,000+", "location": "Mt Eden, Auckland", "description": "Full kitchen replacement including cabinets, benchtop, sink and appliances. Approx 5m x 3m kitchen space.", "posted": "2 hours ago"},
            {"source": "NoCowboys", "title": "Painters needed for exterior repaint", "category": "painting", "budget": "$4,500 - $6,500", "location": "Remuera, Auckland", "description": "2-story weatherboard home, exterior repaint. Prep and 2 coats. Includes minor timber repairs.", "posted": "5 hours ago"},
            {"source": "Neighbourly", "title": "Emergency plumbing - burst pipe", "category": "plumbing", "budget": "Urgent", "location": "Ponsonby, Auckland", "description": "Burst pipe under kitchen sink. Water shut off. Need someone ASAP.", "posted": "12 minutes ago"},
            {"source": "Trade Me", "title": "Bathroom retile", "category": "bathroom", "budget": "$3,500 - $5,000", "location": "Grey Lynn, Auckland", "description": "Small ensuite bathroom retile. Floor + walls. Waterproofing required.", "posted": "1 day ago"},
            {"source": "Builderscrack", "title": "Heat pump service and clean", "category": "hvac", "budget": "$150 - $250", "location": "Epsom, Auckland", "description": "Annual service of Mitsubishi 5kW heat pump. Filter clean, gas check, drain test.", "posted": "3 days ago"},
            {"source": "NoCowboys", "title": "Deck build 4m x 3m", "category": "carpentry", "budget": "$6,000 - $9,000", "location": "Titirangi, Auckland", "description": "Build a new hardwood deck attached to existing house. Materials supplied.", "posted": "6 hours ago"},
        ]
        for e in externals:
            await db.external_jobs.insert_one({
                "external_id": f"ext_{uuid.uuid4().hex[:8]}",
                "created_at": datetime.now(timezone.utc),
                **e,
            })

    # FORUM POSTS (property maintenance & renovations focus)
    if await db.forum_posts.count_documents({}) == 0:
        # Pull existing provider + customer users for realistic authorship
        providers = await db.provider_profiles.find({}, {"_id": 0}).to_list(20)
        customers = await db.users.find({"role": {"$in": ["customer", "landlord", "property"]}}, {"_id": 0}).to_list(20)

        def _author(role: str, idx: int) -> Dict[str, Any]:
            if role == "provider" and providers:
                pr = providers[idx % len(providers)]
                return {"author_id": pr["user_id"], "author_name": pr["business_name"], "author_role": "provider"}
            if customers:
                c = customers[idx % len(customers)]
                return {"author_id": c["user_id"], "author_name": c.get("name", "Homeowner"), "author_role": c.get("role", "customer")}
            # fallback synthetic
            return {"author_id": f"seed_{uuid.uuid4().hex[:8]}", "author_name": ["Emma T.", "Jack R.", "Priya S.", "Ben M.", "Anna K."][idx % 5], "author_role": role}

        provider_seed = [
            {"category": "pricing", "title": "Fair call-out fee in Auckland 2026 — what's your number?",
             "body": "Been holding at $85 for 3 years. Fuel + van maintenance up ~30%. Thinking of moving to $110 for CBD/Northshore, $95 for South Auckland. What's everyone charging right now? Also — do you waive it if the job goes ahead?",
             "tags": ["pricing", "auckland", "call-out"], "up": 156, "down": 4, "views": 812, "replies": 42, "days_ago": 0.1},
            {"category": "reno-projects", "title": "Full bathroom reno case study — $22k, 9 working days, small ensuite",
             "body": "Just wrapped a small ensuite reno in Grey Lynn. Sharing the full breakdown:\n\n• Strip-out & waste: $1,400\n• Waterproofing (2 coats): $900\n• Tiles + adhesive (25m²): $3,200\n• Vanity + tapware + mirror: $2,600\n• Toilet + install: $1,100\n• Shower screen (frameless): $2,200\n• Plumbing labour: $3,800\n• Tiling labour: $4,500\n• Painting + finishing: $1,300\n• Skip + rubbish: $600\n• Markup + profit: $400\n\nAny things you'd cost differently? Owner was stoked — 5★ review + 2 referrals already.",
             "tags": ["bathroom", "renovation", "case-study"], "up": 240, "down": 3, "views": 1420, "replies": 87, "days_ago": 0.4, "pinned": True},
            {"category": "compliance", "title": "Healthy Homes deadline crunch — what landlords are asking",
             "body": "Since Feb 2026 the compliance rate has spiked. Getting daily calls from landlords panic-fixing insulation, extraction fans, moisture barriers.\n\nAvg job: $1,800–$3,200. Insulation top-ups the biggest earner. Make sure you're pulling a compliance statement PDF at handover — saves 40 min back-and-forth per job.",
             "tags": ["healthy-homes", "landlord", "compliance"], "up": 91, "down": 2, "views": 618, "replies": 33, "days_ago": 1.2},
            {"category": "market-trends", "title": "Heat pump servicing demand is up 40% YoY — anyone else?",
             "body": "Winter's coming and my inbox is on fire. Servicing (not new installs) has doubled since last April. Filter cleans + gas check + drain flush = $180–$220 average, 45 min in-and-out.\n\nWhat's driving it? I think Healthy Homes + more heat pumps installed 5+ years ago hitting service age.",
             "tags": ["heat-pump", "hvac", "demand"], "up": 44, "down": 1, "views": 302, "replies": 15, "days_ago": 1.5},
            {"category": "suppliers", "title": "Mitre 10 Trade vs Bunnings Powerpass — real numbers",
             "body": "Ran a side-by-side for 3 months on the same basket (framing timber, GIB, screws, insulation). Powerpass came out 6% cheaper on materials, but Mitre 10 has better delivery windows in Auckland (next-day vs 2–3 day). If you're doing volume, Placemakers still beats both on framing timber. Anyone got the ITM data?",
             "tags": ["suppliers", "materials"], "up": 68, "down": 3, "views": 410, "replies": 21, "days_ago": 3.0},
            {"category": "business", "title": "Late-paying clients — my 3-step process that gets 95% paid in 14 days",
             "body": "After 6 years of chasing invoices I finally have a system:\n\n1) Deposit + progress + final structure written into the quote (30/40/30). Sign before work starts.\n2) Auto-reminder at day 7 & 14 (Xero does this free).\n3) At day 21: a phone call, not email. Human voice = payment 80% of the time. Day 30 = Baycorp letter (costs $19, works).\n\nHappy to share the email templates.",
             "tags": ["business", "invoicing", "cashflow"], "up": 210, "down": 5, "views": 1100, "replies": 64, "days_ago": 4.0},
            {"category": "tools-materials", "title": "Milwaukee M18 vs Makita LXT — 2026 verdict after 18 months",
             "body": "Ran both platforms side-by-side on our crew. Milwaukee wins on impact driver torque (curse of the exhaust brake screws). Makita wins on battery life + charger network. For an all-day tradie: Makita. For heavy demolition: Milwaukee. DeWalt XR is the dark horse — cheaper this year and warranty is easier to claim.",
             "tags": ["tools", "cordless", "reviews"], "up": 88, "down": 12, "views": 545, "replies": 39, "days_ago": 5.0},
            {"category": "maintenance-ops", "title": "Route optimisation cut my drive time 22% — free tool",
             "body": "I was doing 3 unrelated suburbs a day. Started clustering by suburb + using Google Routes API (free tier is enough for a 1-van op). Went from ~45km/day to 35km. That's 2 extra jobs a week, ~$1,200/mo more revenue for the same effort. If you use Servicem8 the routing add-on is $12/mo and does the same thing.",
             "tags": ["operations", "routing", "efficiency"], "up": 55, "down": 2, "views": 288, "replies": 18, "days_ago": 6.5},
            {"category": "smoko-room", "title": "Weirdest thing you've found behind a wall?",
             "body": "Ripped out a bathroom wall in Devonport last week and found a 1970s newspaper wrapped around a beer bottle with a note: 'Sorry future guy, ran out of GIB.' 😂 What have you all uncovered?",
             "tags": ["banter"], "up": 178, "down": 1, "views": 890, "replies": 92, "days_ago": 2.0},
        ]

        customer_seed = [
            {"category": "cost-questions", "title": "Is $28k reasonable for a full bathroom reno? Grey Lynn villa",
             "body": "Got 3 quotes for our upstairs bathroom (small, 3.2m x 2.4m):\n\n• Quote A: $24,500 (mid-range fixtures, 3 weeks)\n• Quote B: $28,900 (premium fixtures, 2.5 weeks, better warranty)\n• Quote C: $19,200 (basic fixtures, 4 weeks, no waterproofing warranty)\n\nLeaning towards B but budget is tight. Anyone renovated recently in the inner suburbs — what did you actually pay?",
             "tags": ["bathroom", "quotes", "budget"], "up": 89, "down": 1, "views": 542, "replies": 34, "days_ago": 0.3},
            {"category": "renovations", "title": "Our 12-month kitchen renovation journey (before/after + full budget)",
             "body": "We finally finished! Started July 2025, wrapped last month. TL;DR: budget was $45k, spent $58k, worth every dollar.\n\nBiggest surprises:\n1) Electrical rewire added $6k we didn't budget for (1962 house)\n2) Waited 11 weeks for the stone benchtop — plan ahead\n3) Living without a kitchen for 3 months was harder than we thought — we had a microwave + air fryer set up in the garage\n\nDM if you want the full spreadsheet, happy to share.",
             "tags": ["kitchen", "renovation", "before-after"], "up": 312, "down": 2, "views": 2100, "replies": 118, "days_ago": 1.0, "pinned": True},
            {"category": "maintenance", "title": "Autumn maintenance checklist — what am I missing?",
             "body": "Made this list for our house before winter hits:\n\n☐ Clean gutters + downpipes\n☐ Service heat pump (filter + gas)\n☐ Check roof for loose flashings\n☐ Reseal windows (silicone perishing)\n☐ Bleed radiators\n☐ Chimney sweep (open fire)\n☐ Insulation top-up in ceiling\n☐ Test smoke alarms + replace batteries\n\nWhat else should I be doing? First winter in this house.",
             "tags": ["maintenance", "seasonal", "winter"], "up": 67, "down": 0, "views": 380, "replies": 28, "days_ago": 2.0},
            {"category": "diy-vs-pro", "title": "Painting the exterior of a 2-storey — DIY or hire?",
             "body": "It's a 1970s weatherboard, ~180m² external wall area. Quotes are $6,500–$9,500. I've painted the interior myself. Am I insane to think I could do this in a couple of weekends with scaffolding hire? Or is this a rookie trap?",
             "tags": ["painting", "diy", "exterior"], "up": 45, "down": 1, "views": 288, "replies": 41, "days_ago": 2.5},
            {"category": "reviews", "title": "★★★★★ Sarah Chen Plumbing — burst pipe emergency, showed up in 40 min",
             "body": "3am on Sunday, pipe burst in the wall. Called Pro Finder NZ, Sarah's team dispatched within 20 min, on site in 40. Fixed it in an hour, minimal drywall damage, invoice was FAIR ($480 total incl after-hours). Cannot recommend enough. Booking her for our bathroom reno next month.",
             "tags": ["review", "plumbing", "emergency"], "up": 156, "down": 0, "views": 720, "replies": 22, "days_ago": 3.0},
            {"category": "smart-home", "title": "Heat pump vs central heating in a 1930s villa — 2 years in",
             "body": "We put in 3x Mitsubishi 5kW units instead of central. Total install cost $9,800 (subsidised).\n\nRunning costs Y1: $1,820. Y2: $1,650. Insulation matters more than the unit itself.\n\nRegrets? One — we should've done ceiling underlay before the heat pumps, not after. Would've saved $400/yr from day 1.",
             "tags": ["heat-pump", "insulation", "efficiency"], "up": 128, "down": 3, "views": 645, "replies": 53, "days_ago": 4.0},
            {"category": "landlord-corner", "title": "Healthy Homes compliance — DIY checklist for landlords",
             "body": "Just did compliance on my rental in Papakura. Total cost: $2,400 (insulation top-up + 2 extraction fans + moisture barrier). Sharing the checklist I used:\n\n• Ceiling insulation R2.9+\n• Underfloor R1.3+ (if accessible)\n• Extraction in kitchen (150mm+ vented outside)\n• Extraction in bathroom (120mm+)\n• Ground moisture barrier (150μm poly)\n• Draught stopping on doors + windows\n• Fixed heater in main living (heat pump ≥1.5kW per m² of floor)\n\nGet compliance statement PDF from your tradie — you'll need it if audited.",
             "tags": ["landlord", "healthy-homes", "compliance"], "up": 94, "down": 1, "views": 480, "replies": 31, "days_ago": 5.0},
            {"category": "disputes", "title": "Tiler left grout uneven — what are my rights?",
             "body": "Paid $4,200 for bathroom tiling. Grout lines are visibly uneven (some 2mm, some 5mm) and one corner has cracked already after 3 weeks. Tiler says 'that's normal'. Is it? What's the process — call DBH, small claims, or file dispute through Pro Finder NZ's mediation?",
             "tags": ["dispute", "warranty", "tiling"], "up": 33, "down": 0, "views": 210, "replies": 47, "days_ago": 6.0},
            {"category": "maintenance", "title": "Best drain camera for renters — recommendations?",
             "body": "Our shower drain blocks every 2 months. Landlord won't send anyone until it's fully blocked. Thinking of buying a cheap borescope to see what's going on. Anything under $150 that actually works? Or is this a false economy?",
             "tags": ["drains", "diy"], "up": 22, "down": 0, "views": 145, "replies": 19, "days_ago": 7.0},
        ]

        replies_pool = [
            "Great writeup, really useful. Bookmarking.",
            "I'd add — always get the compliance PDF at handover. Some tradies forget and it's a nightmare later.",
            "Interesting perspective. My numbers are pretty similar for Wellington market.",
            "Just did something similar. Total came in 10% under yours — happy to share supplier list.",
            "Have you tried getting a second opinion? Sounds like it might be worth it.",
            "Solid advice, thanks for sharing.",
            "This is why I love this forum. Real numbers, real experience.",
            "What software are you using for the quoting side of this?",
            "100% agree. Been doing it this way for 4 years now.",
            "Would love to see the spreadsheet if you're happy to share.",
        ]

        for i, sp in enumerate(provider_seed):
            author = _author("provider", i)
            now = datetime.now(timezone.utc) - timedelta(days=sp["days_ago"])
            post = {
                "post_id": f"fp_{uuid.uuid4().hex[:12]}",
                "audience": "provider",
                "category": sp["category"],
                "title": sp["title"],
                "body": sp["body"],
                "tags": sp["tags"],
                **author,
                "upvotes": sp["up"],
                "downvotes": sp["down"],
                "voters": [],
                "replies_count": sp.get("replies", 0),
                "views": sp["views"],
                "pinned": sp.get("pinned", False),
                "created_at": now,
                "updated_at": now,
                "hot_score": 0.0,
            }
            post["hot_score"] = _hot_score(post)
            await db.forum_posts.insert_one(post)
            # Seed 3 replies per post for realistic thread
            for j in range(3):
                r_author = _author("provider" if j % 2 == 0 else "customer", i + j + 1)
                await db.forum_replies.insert_one({
                    "reply_id": f"fr_{uuid.uuid4().hex[:12]}",
                    "post_id": post["post_id"],
                    "parent_reply_id": None,
                    **r_author,
                    "body": replies_pool[(i + j) % len(replies_pool)],
                    "upvotes": max(1, sp["up"] // (6 + j * 4)),
                    "downvotes": 0,
                    "voters": [],
                    "created_at": now + timedelta(hours=j * 2 + 1),
                })

        for i, sp in enumerate(customer_seed):
            author = _author("customer", i)
            now = datetime.now(timezone.utc) - timedelta(days=sp["days_ago"])
            post = {
                "post_id": f"fp_{uuid.uuid4().hex[:12]}",
                "audience": "customer",
                "category": sp["category"],
                "title": sp["title"],
                "body": sp["body"],
                "tags": sp["tags"],
                **author,
                "upvotes": sp["up"],
                "downvotes": sp["down"],
                "voters": [],
                "replies_count": sp.get("replies", 0),
                "views": sp["views"],
                "pinned": sp.get("pinned", False),
                "created_at": now,
                "updated_at": now,
                "hot_score": 0.0,
            }
            post["hot_score"] = _hot_score(post)
            await db.forum_posts.insert_one(post)
            for j in range(3):
                r_author = _author("provider" if j == 1 else "customer", i + j + 2)
                await db.forum_replies.insert_one({
                    "reply_id": f"fr_{uuid.uuid4().hex[:12]}",
                    "post_id": post["post_id"],
                    "parent_reply_id": None,
                    **r_author,
                    "body": replies_pool[(i * 2 + j) % len(replies_pool)],
                    "upvotes": max(1, sp["up"] // (5 + j * 3)),
                    "downvotes": 0,
                    "voters": [],
                    "created_at": now + timedelta(hours=j * 3 + 2),
                })


@app.on_event("startup")
async def on_startup():
    await seed_data()
    await seed_demo_accounts()
    logging.info("Pro Finder NZ startup complete")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
