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

from html import escape  # noqa: E402
from email_service import send_email, EMAIL_FROM_NAME  # noqa: E402
from storage_service import init_storage, put_object, get_object, APP_NAME  # noqa: E402

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
    account_type: Optional[str] = None           # residential | commercial
    business_name: Optional[str] = None          # providers / companies
    signup_details: Dict[str, Any] = {}          # role-specific answers from the signup flow


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
    property_id: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    # ---- Job size / pricing + matching engine ----
    pricing_type: str = "large_quote"            # small_fixed | hourly | large_quote
    budget_or_estimate: Optional[float] = None   # target fixed price ($) or estimated hours
    preferred_date: Optional[str] = None         # ISO date (YYYY-MM-DD)
    location_suburb: Optional[str] = None
    client_type: str = "residential"             # mirrors service_type
    matched_count: int = 0                       # specialised pros notified by the dispatcher
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
    property_id: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    pricing_type: str = "large_quote"
    budget_or_estimate: Optional[float] = None
    preferred_date: Optional[str] = None
    location_suburb: Optional[str] = None
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
    name: Optional[str] = None              # e.g. "Home", "Rental – Ponsonby"
    property_type: str = "residential"
    size: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    access_notes: Optional[str] = None      # gate codes, pets, parking
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_primary: bool = False                # one main property per owner
    tenants: List[Dict[str, str]] = []
    jobs_count: int = 0
    total_spent: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PropertyCreate(BaseModel):
    address: str
    name: Optional[str] = None
    property_type: str = "residential"
    size: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    access_notes: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_primary: bool = False


class PropertyUpdate(BaseModel):
    address: Optional[str] = None
    name: Optional[str] = None
    property_type: Optional[str] = None
    size: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    access_notes: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


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
    payload.email = payload.email.strip().lower()
    if payload.role not in SIGNUP_ROLES:
        raise HTTPException(status_code=400, detail="Unknown account type")
    if len(payload.password or "") < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
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
        **_signup_fields(payload.role, payload.account_type, payload.business_name, payload.signup_details),
    }
    await db.users.insert_one(doc)
    # If provider role, create provider profile
    if payload.role == "provider":
        await db.provider_profiles.insert_one({
            "user_id": user_id,
            "business_name": (payload.business_name or "").strip() or payload.name,
            "categories": [],
            "hourly_rate": 85.0,
            "rating": 0.0,
            "reviews_count": 0,
            "jobs_completed": 0,
            "verified": False,
            "qualified_verified": False,
            "police_checked": False,
            "insured": False,
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
    return {"user": {**doc, "is_reviewer": is_reviewer(doc)}, "token": token}


@api.post("/auth/login")
async def login(payload: UserLogin, response: Response):
    email = payload.email.strip()
    user = await db.users.find_one({"email": email.lower()}) or await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(user["user_id"])
    set_auth_cookie(response, token)
    user.pop("_id", None)
    user.pop("password_hash", None)
    return {"user": {**user, "is_reviewer": is_reviewer(user)}, "token": token}


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
    if user.get("role") != role:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"role": role}})
        user["role"] = role
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
            "role": role if role in SIGNUP_ROLES else "customer",
            "phone": None,
            "city": "Auckland",
            "signup_complete": False,   # role-specific details are sent next via /auth/complete-signup
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
                "rating": 0.0,
                "reviews_count": 0,
                "jobs_completed": 0,
                "verified": False,
                "qualified_verified": False,
                "police_checked": False,
                "insured": False,
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
    user.pop("password_hash", None)
    return {"user": {**user, "is_reviewer": is_reviewer(user)}, "session_token": session_token}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {**user, "is_reviewer": is_reviewer(user)}


SIGNUP_ROLES = ("customer", "provider", "property", "landlord", "facilities", "insurance")
SIGNUP_DETAIL_KEYS = {
    "customer": ["suburb", "home_type"],
    "landlord": ["rental_count", "suburb"],
    "property": ["company_name", "properties_managed", "suburb"],
    "facilities": ["organisation", "buildings_count", "suburb"],
    "insurance": ["company_name", "fsp_number", "claims_per_month"],
    "provider": ["nzbn", "trade_licence", "years_in_business", "suburb"],
}


def is_reviewer(user: Optional[Dict[str, Any]]) -> bool:
    emails = {e.strip().lower() for e in (os.environ.get("REVIEWER_EMAILS") or "").split(",") if e.strip()}
    return bool(user and (user.get("email") or "").lower() in emails)


def _signup_fields(role: str, account_type: Optional[str], business_name: Optional[str], details: Dict[str, Any]) -> Dict[str, Any]:
    allowed = SIGNUP_DETAIL_KEYS.get(role, [])
    clean = {k: (str(v).strip()[:200] if v is not None else None) for k, v in (details or {}).items() if k in allowed}
    at = account_type if account_type in ("residential", "commercial") else ("commercial" if role in ("facilities",) else "residential")
    out = {"account_type": at, "signup_details": clean, "signup_complete": True}
    if business_name and business_name.strip():
        out["business_name"] = business_name.strip()[:120]
    return out


class SignupCompleteIn(BaseModel):
    role: str
    name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    account_type: Optional[str] = None
    business_name: Optional[str] = None
    signup_details: Dict[str, Any] = {}


@api.post("/auth/complete-signup")
async def complete_signup(payload: SignupCompleteIn, user=Depends(require_user)):
    """Used after Google sign-up: stores the role-specific details collected before the redirect."""
    if payload.role not in SIGNUP_ROLES:
        raise HTTPException(status_code=400, detail="Unknown account type")
    if user.get("signup_complete") is not False and user.get("role") != payload.role:
        raise HTTPException(status_code=400, detail="This account already has a different account type")
    upd = _signup_fields(payload.role, payload.account_type, payload.business_name, payload.signup_details)
    upd["role"] = payload.role
    for k in ("name", "phone", "city"):
        v = getattr(payload, k)
        if v and v.strip():
            upd[k] = v.strip()[:120]
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": upd})
    if payload.role == "provider":
        await db.provider_profiles.update_one({"user_id": user["user_id"]}, {
            "$set": {"business_name": upd.get("business_name") or upd.get("name") or user.get("name")},
            "$setOnInsert": {"categories": [], "hourly_rate": 85.0, "rating": 0.0, "reviews_count": 0, "jobs_completed": 0,
                             "verified": False, "qualified_verified": False, "police_checked": False, "insured": False,
                             "plan": "free", "online": False, "bio": ""}}, upsert=True)
    u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return {**u, "is_reviewer": is_reviewer(u)}


# ---------------- PROVIDER DOCUMENTS (qualifications, certifications, police check) ----------------
DOC_KINDS = ("qualification", "certification", "police_check")


class ProviderDocIn(BaseModel):
    kind: str
    title: str
    issuer: Optional[str] = None
    reference: Optional[str] = None
    expiry: Optional[str] = None
    file_url: str
    file_name: Optional[str] = None


async def _refresh_provider_ticks(provider_id: str):
    approved = await db.provider_documents.find({"provider_id": provider_id, "status": "approved"}, {"kind": 1, "_id": 0}).to_list(None)
    kinds = {d["kind"] for d in approved}
    qualified = bool(kinds & {"qualification", "certification"})
    police = "police_check" in kinds
    await db.provider_profiles.update_one({"user_id": provider_id}, {"$set": {
        "qualified_verified": qualified, "police_checked": police}})


@api.get("/providers/me/documents")
async def my_documents(user=Depends(require_user)):
    await _require_provider(user)
    return await db.provider_documents.find({"provider_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.post("/providers/me/documents")
async def add_document(payload: ProviderDocIn, user=Depends(require_user)):
    await _require_provider(user)
    if payload.kind not in DOC_KINDS:
        raise HTTPException(status_code=400, detail="kind must be qualification, certification or police_check")
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Please give the document a name")
    if not payload.file_url.startswith("/api/files/"):
        raise HTTPException(status_code=400, detail="Upload the document file first")
    fid = payload.file_url.split("/")[3]
    rec = await db.files.find_one({"file_id": fid}, {"_id": 0, "owner_id": 1})
    if not rec or rec.get("owner_id") != user["user_id"]:
        raise HTTPException(status_code=400, detail="File not found")
    doc = {"doc_id": f"doc_{uuid.uuid4().hex[:10]}", "provider_id": user["user_id"], "kind": payload.kind,
           "title": payload.title.strip()[:120], "issuer": (payload.issuer or "").strip()[:120] or None,
           "reference": (payload.reference or "").strip()[:80] or None, "expiry": payload.expiry or None,
           "file_url": payload.file_url, "file_name": (payload.file_name or "")[:200] or None,
           "status": "pending", "review_note": None, "created_at": datetime.now(timezone.utc),
           "reviewed_at": None, "reviewed_by": None}
    await db.provider_documents.insert_one(dict(doc))
    for email in [e.strip().lower() for e in (os.environ.get("REVIEWER_EMAILS") or "").split(",") if e.strip()]:
        rv = await db.users.find_one({"email": email}, {"user_id": 1, "_id": 0})
        if rv:
            await notify(rv["user_id"], "doc_review", "New document to review", f"{doc['title']} · {user.get('name')}", "/review/documents")
    return doc


@api.delete("/providers/me/documents/{doc_id}")
async def delete_document(doc_id: str, user=Depends(require_user)):
    await _require_provider(user)
    r = await db.provider_documents.delete_one({"doc_id": doc_id, "provider_id": user["user_id"]})
    if not r.deleted_count:
        raise HTTPException(status_code=404, detail="Document not found")
    await _refresh_provider_ticks(user["user_id"])
    return {"ok": True}


@api.get("/providers/{provider_id}/credentials")
async def provider_credentials(provider_id: str, user=Depends(require_user)):
    prof = await db.provider_profiles.find_one({"user_id": provider_id}, {"_id": 0, "qualified_verified": 1, "police_checked": 1})
    if prof is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    approved = await db.provider_documents.find({"provider_id": provider_id, "status": "approved"},
                                                {"_id": 0, "kind": 1, "title": 1, "issuer": 1, "expiry": 1}).to_list(50)
    return {"qualified": bool(prof.get("qualified_verified")), "police_checked": bool(prof.get("police_checked")), "documents": approved}


async def _require_reviewer(user):
    if not is_reviewer(user):
        raise HTTPException(status_code=403, detail="Only document reviewers can do this")


@api.get("/review/documents")
async def review_queue(status: str = "pending", user=Depends(require_user)):
    await _require_reviewer(user)
    q = {} if status == "all" else {"status": status}
    docs = await db.provider_documents.find(q, {"_id": 0}).sort("created_at", 1).to_list(500)
    profs = await db.provider_profiles.find({"user_id": {"$in": list({d["provider_id"] for d in docs})}},
                                            {"_id": 0, "user_id": 1, "business_name": 1}).to_list(None)
    pm = {p["user_id"]: p.get("business_name") for p in profs}
    for d in docs:
        d["provider_name"] = pm.get(d["provider_id"], "")
    return docs


class ReviewIn(BaseModel):
    decision: str  # approve | reject
    note: Optional[str] = None


@api.post("/review/documents/{doc_id}")
async def review_document(doc_id: str, payload: ReviewIn, user=Depends(require_user)):
    await _require_reviewer(user)
    if payload.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be approve or reject")
    d = await db.provider_documents.find_one({"doc_id": doc_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    if payload.decision == "reject" and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail="Add a short reason so the provider can fix it")
    status = "approved" if payload.decision == "approve" else "rejected"
    await db.provider_documents.update_one({"doc_id": doc_id}, {"$set": {
        "status": status, "review_note": (payload.note or "").strip()[:500] or None,
        "reviewed_at": datetime.now(timezone.utc), "reviewed_by": user["email"]}})
    await _refresh_provider_ticks(d["provider_id"])
    await notify(d["provider_id"], "doc_reviewed", f"{d['title']} {'approved ✓' if status == 'approved' else 'needs attention'}",
                 payload.note or "", "/provider/verification")
    return {"ok": True, "status": status}


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
                "rating": 0.0,
                "reviews_count": 0,
                "jobs_completed": 0,
                "verified": False, "qualified_verified": False, "police_checked": False,
                "insured": False,
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
    if payload.pricing_type not in PRICING_TYPES:
        raise HTTPException(status_code=400, detail="pricing_type must be small_fixed, hourly or large_quote")
    if payload.budget_or_estimate is not None and not (0 < payload.budget_or_estimate <= 10_000_000):
        raise HTTPException(status_code=400, detail="budget_or_estimate must be a positive number")
    if payload.preferred_date:
        try:
            datetime.strptime(payload.preferred_date[:10], "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="preferred_date must be YYYY-MM-DD")
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
    access_notes: Optional[str] = None
    if payload.property_id:
        prop = await db.properties.find_one({"property_id": payload.property_id, "owner_id": user["user_id"]})
        if not prop:
            raise HTTPException(status_code=400, detail="Property not found on your profile")
        access_notes = prop.get("access_notes")
        if prop.get("lat") is not None and job_data.get("location_lat") is None:
            job_data["location_lat"], job_data["location_lng"] = prop.get("lat"), prop.get("lng")
    job = JobPost(
        client_id=user["user_id"],
        tenant_id=user["user_id"] if approval_status == "pending" else None,
        tenancy_id=tenancy_id,
        approver_id=approver_id,
        approval_status=approval_status,
        billing_target=billing_target,
        **job_data,
    )
    doc = job.dict()
    doc["client_type"] = payload.service_type
    doc["access_notes"] = access_notes  # private: only shown to the client, approver and winning pro
    await db.jobs.insert_one(doc)
    if approval_status != "pending":  # pending jobs are dispatched once the manager approves
        doc["matched_count"] = await dispatch_job(doc)
        if doc["matched_count"]:
            doc["status"] = "matched"
    return {k: v for k, v in doc.items() if k not in ("_id",)}


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
        "status": {"$in": ["open", "matched"]},
        "approval_status": {"$in": ["not_required", "approved"]},
    }
    if category:
        q["category"] = category
    jobs = await db.jobs.find(q, {"_id": 0, "access_notes": 0}).sort("created_at", -1).to_list(200)
    return jobs


@api.get("/jobs/{job_id}")
async def get_job(job_id: str, user=Depends(require_user)):
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    bids = await db.bids.find({"job_id": job_id}, {"_id": 0}).sort("created_at", -1).to_list(None)
    can_see_access = user["user_id"] in (job.get("client_id"), job.get("approver_id")) or any(
        b.get("provider_id") == user["user_id"] and b.get("status") == "accepted" for b in bids)
    if not can_see_access:
        job.pop("access_notes", None)
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
    await db.job_matches.delete_many({"job_id": job_id})
    await db.notifications.delete_many({"link": f"/jobs/{job_id}"})
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
    if job.get("status") not in ("open", "matched"):
        raise HTTPException(status_code=400, detail="This job has already been awarded")
    await db.bids.update_one({"bid_id": bid_id}, {"$set": {"status": "accepted"}})
    await db.jobs.update_one({"job_id": bid["job_id"]}, {"$set": {"status": "in_progress", "assigned_provider_id": bid["provider_id"]}})
    # Close the dispatch queue for everyone else
    await db.job_matches.update_many({"job_id": bid["job_id"], "provider_id": {"$ne": bid["provider_id"]}}, {"$set": {"match_status": "closed"}})
    await db.job_matches.update_many({"job_id": bid["job_id"], "provider_id": bid["provider_id"]}, {"$set": {"match_status": "awarded"}})
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
        job = jobs_map.get(b["job_id"])
        if job is not None and b.get("status") != "accepted":
            job = {k: v for k, v in job.items() if k != "access_notes"}  # private until hired
        b["job"] = job
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
def _validate_property_fields(data: Dict[str, Any]):
    if "property_type" in data and data["property_type"] not in ("residential", "commercial"):
        raise HTTPException(status_code=400, detail="property_type must be 'residential' or 'commercial'")
    if "address" in data and not (data["address"] or "").strip():
        raise HTTPException(status_code=400, detail="Address is required")
    for k in ("bedrooms", "bathrooms"):
        if data.get(k) is not None and (data[k] < 0 or data[k] > 100):
            raise HTTPException(status_code=400, detail=f"{k} must be between 0 and 100")


@api.post("/properties")
async def create_property(payload: PropertyCreate, user=Depends(require_user)):
    data = payload.dict()
    _validate_property_fields(data)
    data["address"] = data["address"].strip()
    has_any = await db.properties.count_documents({"owner_id": user["user_id"]})
    if not has_any:
        data["is_primary"] = True  # first property is the main one
    elif data.get("is_primary"):
        await db.properties.update_many({"owner_id": user["user_id"]}, {"$set": {"is_primary": False}})
    prop = Property(owner_id=user["user_id"], **data)
    await db.properties.insert_one(prop.dict())
    return prop


@api.get("/properties/mine")
async def my_properties(user=Depends(require_user)):
    props = await db.properties.find({"owner_id": user["user_id"]}, {"_id": 0}).sort([("is_primary", -1), ("created_at", 1)]).to_list(500)
    return props


@api.patch("/properties/{property_id}")
async def update_property(property_id: str, payload: PropertyUpdate, user=Depends(require_user)):
    p = await db.properties.find_one({"property_id": property_id})
    if not p or p["owner_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Property not found")
    data = payload.dict(exclude_unset=True)
    _validate_property_fields(data)
    if "address" in data:
        data["address"] = data["address"].strip()
    if data:
        await db.properties.update_one({"property_id": property_id}, {"$set": data})
    return await db.properties.find_one({"property_id": property_id}, {"_id": 0})


@api.post("/properties/{property_id}/primary")
async def make_primary_property(property_id: str, user=Depends(require_user)):
    p = await db.properties.find_one({"property_id": property_id})
    if not p or p["owner_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Property not found")
    await db.properties.update_many({"owner_id": user["user_id"]}, {"$set": {"is_primary": False}})
    await db.properties.update_one({"property_id": property_id}, {"$set": {"is_primary": True}})
    return {"ok": True}


@api.delete("/properties/{property_id}")
async def delete_property(property_id: str, user=Depends(require_user)):
    p = await db.properties.find_one({"property_id": property_id})
    if not p or p["owner_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Property not found")
    await db.properties.delete_one({"property_id": property_id})
    if p.get("is_primary"):
        nxt = await db.properties.find_one({"owner_id": user["user_id"]}, sort=[("created_at", 1)])
        if nxt:
            await db.properties.update_one({"property_id": nxt["property_id"]}, {"$set": {"is_primary": True}})
    return {"ok": True}


# ---------------- ADDRESS SEARCH ----------------
# Google Places (New) when GOOGLE_MAPS_API_KEY is set, otherwise free OpenStreetMap (Photon) search.
NZ_BBOX = "166.0,-47.5,179.0,-34.0"
OSM_UA = {"User-Agent": "ProFinderNZ/1.0 (address search)"}


_GOOGLE_DISABLED_UNTIL: Dict[str, datetime] = {}  # key -> time; skip Google briefly after an auth failure


def _google_key() -> str:
    k = (os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()
    until = _GOOGLE_DISABLED_UNTIL.get(k)
    if k and until and until > datetime.now(timezone.utc):
        return ""
    return k


def _photon_label(p: Dict[str, Any]) -> Dict[str, str]:
    street = " ".join(x for x in [p.get("housenumber"), p.get("street")] if x)
    main = street or p.get("name") or ""
    if p.get("name") and street and p.get("name") != street:
        main = f"{street}"
    area = [p.get("locality") or p.get("district"), p.get("city") or p.get("county"), p.get("postcode")]
    secondary = ", ".join(dict.fromkeys(x for x in area if x and x != main))
    return {"main": main or secondary, "secondary": secondary}


async def _photon_search(q: str) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=6.0) as client:
        r = await client.get("https://photon.komoot.io/api/", params={"q": q, "limit": 8, "bbox": NZ_BBOX, "lang": "en"}, headers=OSM_UA)
        r.raise_for_status()
        feats = r.json().get("features", [])
    out, seen = [], set()
    for f in feats:
        p = f.get("properties", {})
        if (p.get("countrycode") or "").upper() != "NZ":
            continue
        lbl = _photon_label(p)
        full = ", ".join(x for x in [lbl["main"], lbl["secondary"]] if x)
        if not full or full in seen:
            continue
        seen.add(full)
        lng, lat = (f.get("geometry", {}).get("coordinates") or [None, None])[:2]
        out.append({"id": f"osm:{p.get('osm_type')}{p.get('osm_id')}", "main": lbl["main"], "secondary": lbl["secondary"],
                    "address": full, "lat": lat, "lng": lng})
    return out[:6]


async def _google_search(q: str, session: Optional[str]) -> List[Dict[str, Any]]:
    body: Dict[str, Any] = {"input": q, "includedRegionCodes": ["nz"], "languageCode": "en"}
    if session:
        body["sessionToken"] = session
    async with httpx.AsyncClient(timeout=6.0) as client:
        r = await client.post("https://places.googleapis.com/v1/places:autocomplete", json=body,
                              headers={"X-Goog-Api-Key": _google_key(), "Content-Type": "application/json"})
        r.raise_for_status()
        sugg = r.json().get("suggestions", [])
    out = []
    for s_ in sugg:
        pp = s_.get("placePrediction")
        if not pp:
            continue
        sf = pp.get("structuredFormat", {})
        out.append({"id": f"g:{pp.get('placeId')}", "main": sf.get("mainText", {}).get("text") or pp.get("text", {}).get("text", ""),
                    "secondary": sf.get("secondaryText", {}).get("text", ""), "address": pp.get("text", {}).get("text", ""),
                    "lat": None, "lng": None})
    return out[:6]


async def _nominatim_search(q: str) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=6.0) as client:
        r = await client.get("https://nominatim.openstreetmap.org/search", headers=OSM_UA,
                             params={"q": q, "format": "jsonv2", "countrycodes": "nz", "addressdetails": 1, "limit": 6})
        r.raise_for_status()
        rows = r.json()
    out = []
    for row in rows:
        a = row.get("address", {})
        street = " ".join(x for x in [a.get("house_number"), a.get("road")] if x)
        main = street or row.get("name") or row.get("display_name", "").split(",")[0]
        area = [a.get("suburb") or a.get("neighbourhood"), a.get("city") or a.get("town") or a.get("village"), a.get("postcode")]
        secondary = ", ".join(dict.fromkeys(x for x in area if x and x != main))
        out.append({"id": f"nom:{row.get('osm_type')}{row.get('osm_id')}", "main": main, "secondary": secondary,
                    "address": ", ".join(x for x in [main, secondary] if x),
                    "lat": float(row["lat"]) if row.get("lat") else None, "lng": float(row["lon"]) if row.get("lon") else None})
    return out


@api.get("/address/search")
async def address_search(q: str, session: Optional[str] = None, user=Depends(require_user)):
    q = (q or "").strip()
    if len(q) < 3:
        return {"source": "none", "results": []}
    if _google_key():
        try:
            return {"source": "google", "results": await _google_search(q, session)}
        except Exception as e:  # fall back to free search if Google fails
            logging.warning(f"Google address search failed, falling back to OSM: {e}")
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (400, 401, 403):
                _GOOGLE_DISABLED_UNTIL[(os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()] = datetime.now(timezone.utc) + timedelta(minutes=10)
    try:
        return {"source": "osm", "results": await _photon_search(q)}
    except Exception as e:
        logging.warning(f"Photon address search failed, trying Nominatim: {e}")
    try:
        return {"source": "osm", "results": await _nominatim_search(q)}
    except Exception as e:
        logging.warning(f"Nominatim address search failed: {e}")
        return {"source": "error", "results": []}


@api.get("/address/details")
async def address_details(place_id: str, session: Optional[str] = None, user=Depends(require_user)):
    """Resolve a Google place id to full address + coordinates (OSM results already include them)."""
    if not place_id.startswith("g:") or not _google_key():
        raise HTTPException(status_code=400, detail="Details are only needed for Google results")
    params = {"sessionToken": session} if session else {}
    async with httpx.AsyncClient(timeout=6.0) as client:
        r = await client.get(f"https://places.googleapis.com/v1/places/{place_id[2:]}", params=params,
                             headers={"X-Goog-Api-Key": _google_key(), "X-Goog-FieldMask": "formattedAddress,location"})
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not look up that address")
    d = r.json()
    loc = d.get("location", {})
    return {"address": d.get("formattedAddress"), "lat": loc.get("latitude"), "lng": loc.get("longitude")}


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
# Taxonomy category id -> older provider category slugs still stored on profiles
CATEGORY_ALIASES: Dict[str, List[str]] = {
    "plumbing-gas": ["plumbing"],
    "heating-cooling-ventilation": ["hvac"], "hvac-mechanical": ["hvac"],
    "general-home-maintenance": ["handyman"], "building-maintenance": ["handyman"],
    "painting-interior-finishes": ["painting"], "interior-finishes": ["painting"],
    "roofing-guttering": ["roofing"], "roofing-waterproofing": ["roofing"],
    "gardening-lawn": ["lawn", "gardening"], "grounds-maintenance": ["lawn", "gardening"],
    "landscaping": ["lawn", "landscaping"], "commercial-landscaping": ["lawn", "landscaping"],
    "cleaning": ["cleaning"], "commercial-cleaning": ["cleaning"],
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat, dlng = r2 - r1, math.radians(lng2 - lng1)
    h = math.sin(dlat / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dlng / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


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
    sort: str = "best_match",             # best_match | rating | price_asc | price_desc | reviews | nearest
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    max_km: Optional[float] = None,
    limit: int = 60,
    user=Depends(require_user),
):
    """Customer-facing provider directory search. Filter + sort providers by category/subcategory/etc."""
    query: Dict[str, Any] = {}
    and_: List[Dict[str, Any]] = []
    if category:
        query["categories"] = {"$in": [category, *CATEGORY_ALIASES.get(category, [])]}
    if subcategory:
        # Providers with no listed subcategories cover their whole category
        and_.append({"$or": [{"subcategories": subcategory}, {"subcategories": {"$in": [[], None]}}, {"subcategories": {"$exists": False}}]})
    if verified_only:
        query["verified"] = True
    if q:
        and_.append({"$or": [
            {"business_name": {"$regex": q, "$options": "i"}},
            {"bio": {"$regex": q, "$options": "i"}},
        ]})
    if and_:
        query["$and"] = and_
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
    if lat is not None and lng is not None:
        for p in profiles:
            if p.get("latitude") is not None and p.get("longitude") is not None:
                p["distance_km"] = round(_haversine_km(lat, lng, p["latitude"], p["longitude"]), 1)
        # Providers who set a travel radius only appear to customers inside it
        profiles = [p for p in profiles if not p.get("service_radius_km") or p.get("distance_km") is None or p["distance_km"] <= p["service_radius_km"]]
        if max_km is not None:
            profiles = [p for p in profiles if p.get("distance_km") is not None and p["distance_km"] <= max_km]
    # Sort
    if sort == "nearest":
        profiles.sort(key=lambda p: p.get("distance_km", 1e9))
    elif sort == "rating":
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
    if "availability_status" in body:
        if body["availability_status"] not in AVAILABILITY:
            raise HTTPException(status_code=400, detail="availability_status must be available or busy")
        allowed["availability_status"] = body["availability_status"]
    if "service_radius_km" in body:
        r = body["service_radius_km"]
        if r is not None and (isinstance(r, bool) or not isinstance(r, (int, float)) or not 1 <= r <= 200):
            raise HTTPException(status_code=400, detail="service_radius_km must be between 1 and 200, or null for no limit")
        allowed["service_radius_km"] = r
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


# ---------------- TIMESHEETS ----------------
TIME_ENTRY_TYPES = {"work", "travel", "materials"}
TIME_ENTRY_MODES = {"manual", "geofence"}


def _entry_duration_seconds(entry: Dict[str, Any]) -> int:
    """Compute duration for an entry. Running entries use 'now' as the end."""
    try:
        start = datetime.fromisoformat(entry["started_at"]) if isinstance(entry.get("started_at"), str) else entry["started_at"]
        end_raw = entry.get("ended_at")
        if end_raw:
            end = datetime.fromisoformat(end_raw) if isinstance(end_raw, str) else end_raw
        else:
            end = datetime.now(timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return max(0, int((end - start).total_seconds()))
    except Exception:
        return 0


def _entry_billable_cost(entry: Dict[str, Any]) -> float:
    """Labour cost = rate/hour * minutes/60, rounded to cents. Fuel is added separately."""
    minutes = _entry_duration_seconds(entry) / 60.0
    rate = float(entry.get("hourly_rate_snapshot") or 0)
    labour = round(minutes * (rate / 60.0), 2)
    fuel = float(entry.get("fuel_cost") or 0)
    return round(labour + fuel, 2)


def _serialize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in entry.items() if k != "_id"}
    out["duration_seconds"] = _entry_duration_seconds(entry)
    out["duration_minutes"] = round(out["duration_seconds"] / 60.0, 2)
    out["cost"] = _entry_billable_cost(entry)
    out["is_running"] = entry.get("ended_at") is None
    return out


async def _resolve_worker(provider_id: str, worker_id: Optional[str], user: Dict[str, Any]) -> Dict[str, Any]:
    """Return {worker_id, worker_name, hourly_rate}. Defaults to the provider themselves."""
    if not worker_id or worker_id == provider_id:
        prof = await db.provider_profiles.find_one({"user_id": provider_id}, {"_id": 0})
        return {
            "worker_id": provider_id,
            "worker_name": user.get("name") or (prof or {}).get("business_name") or "You",
            "hourly_rate": float((prof or {}).get("hourly_rate") or 85.0),
        }
    member = await db.team_members.find_one({"member_id": worker_id, "owner_id": provider_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Worker not found on your team")
    return {
        "worker_id": worker_id,
        "worker_name": member["name"],
        "hourly_rate": float(member.get("hourly_rate") or 45.0),
    }


async def _job_snapshot(job_id: Optional[str], provider_id: str) -> Dict[str, Any]:
    if not job_id:
        return {"job_id": None, "job_title": None, "job_address": None, "job_latitude": None, "job_longitude": None}
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        return {"job_id": job_id, "job_title": None, "job_address": None, "job_latitude": None, "job_longitude": None}
    return {
        "job_id": job_id,
        "job_title": job.get("title"),
        "job_address": job.get("address") or job.get("location"),
        "job_latitude": job.get("latitude"),
        "job_longitude": job.get("longitude"),
    }


@api.get("/timesheets/active")
async def timesheets_active(user=Depends(require_user)):
    """Return every currently-running entry for this provider (self + team)."""
    if user["role"] != "provider":
        raise HTTPException(status_code=403, detail="Provider role required")
    entries = await db.time_entries.find(
        {"provider_id": user["user_id"], "ended_at": None},
        {"_id": 0},
    ).sort("started_at", -1).to_list(50)
    return [_serialize_entry(e) for e in entries]


@api.get("/timesheets/entries")
async def timesheets_list(
    job_id: Optional[str] = None,
    worker_id: Optional[str] = None,
    type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500,
    user=Depends(require_user),
):
    if user["role"] != "provider":
        raise HTTPException(status_code=403, detail="Provider role required")
    query: Dict[str, Any] = {"provider_id": user["user_id"]}
    if job_id:
        query["job_id"] = job_id
    if worker_id:
        query["worker_id"] = worker_id
    if type:
        if type not in TIME_ENTRY_TYPES:
            raise HTTPException(status_code=400, detail=f"type must be one of {sorted(TIME_ENTRY_TYPES)}")
        query["type"] = type
    if date_from or date_to:
        rng: Dict[str, Any] = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        query["started_at"] = rng
    entries = await db.time_entries.find(query, {"_id": 0}).sort("started_at", -1).to_list(min(max(limit, 1), 1000))
    return [_serialize_entry(e) for e in entries]


@api.post("/timesheets/start")
async def timesheets_start(payload: Dict[str, Any], user=Depends(require_user)):
    """Start a running timer. Only one active entry per worker at a time."""
    if user["role"] != "provider":
        raise HTTPException(status_code=403, detail="Provider role required")
    entry_type = (payload.get("type") or "work").lower()
    if entry_type not in TIME_ENTRY_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {sorted(TIME_ENTRY_TYPES)}")
    mode = (payload.get("mode") or "manual").lower()
    if mode not in TIME_ENTRY_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {sorted(TIME_ENTRY_MODES)}")
    worker = await _resolve_worker(user["user_id"], payload.get("worker_id"), user)
    # Prevent a double-start for the same worker.
    existing = await db.time_entries.find_one({
        "provider_id": user["user_id"], "worker_id": worker["worker_id"], "ended_at": None,
    }, {"_id": 0})
    if existing:
        return {"ok": False, "error": "already_running", "entry": _serialize_entry(existing)}
    job_snap = await _job_snapshot(payload.get("job_id"), user["user_id"])
    started_at = datetime.now(timezone.utc).isoformat()
    entry = {
        "entry_id": f"te_{uuid.uuid4().hex[:12]}",
        "provider_id": user["user_id"],
        **worker,
        **job_snap,
        "type": entry_type,
        "mode": mode,
        "started_at": started_at,
        "ended_at": None,
        "started_lat": payload.get("lat"),
        "started_lng": payload.get("lng"),
        "ended_lat": None,
        "ended_lng": None,
        "notes": (payload.get("notes") or "").strip() or None,
        "fuel_km": None,
        "fuel_cost": None,
        "hourly_rate_snapshot": worker["hourly_rate"],
        "billable": bool(payload.get("billable", True)),
        "created_at": started_at,
    }
    await db.time_entries.insert_one(entry.copy())
    return {"ok": True, "entry": _serialize_entry(entry)}


@api.post("/timesheets/stop/{entry_id}")
async def timesheets_stop(entry_id: str, payload: Dict[str, Any] | None = None, user=Depends(require_user)):
    entry = await db.time_entries.find_one({"entry_id": entry_id})
    if not entry or entry.get("provider_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.get("ended_at"):
        return {"ok": True, "entry": _serialize_entry(entry)}
    payload = payload or {}
    ended_at = datetime.now(timezone.utc).isoformat()
    update = {
        "ended_at": ended_at,
        "ended_lat": payload.get("lat"),
        "ended_lng": payload.get("lng"),
    }
    if payload.get("notes"):
        update["notes"] = str(payload["notes"]).strip() or entry.get("notes")
    await db.time_entries.update_one({"entry_id": entry_id}, {"$set": update})
    entry.update(update)
    return {"ok": True, "entry": _serialize_entry(entry)}


@api.post("/timesheets/entries")
async def timesheets_create(payload: Dict[str, Any], user=Depends(require_user)):
    """Create a completed entry directly (retro log, travel, materials run with fuel)."""
    if user["role"] != "provider":
        raise HTTPException(status_code=403, detail="Provider role required")
    entry_type = (payload.get("type") or "work").lower()
    if entry_type not in TIME_ENTRY_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {sorted(TIME_ENTRY_TYPES)}")
    if not payload.get("started_at") or not payload.get("ended_at"):
        raise HTTPException(status_code=400, detail="started_at and ended_at are required")
    try:
        if datetime.fromisoformat(str(payload["ended_at"]).replace("Z", "+00:00")) <= datetime.fromisoformat(str(payload["started_at"]).replace("Z", "+00:00")):
            raise HTTPException(status_code=400, detail="ended_at must be after started_at")
        fuel_km = float(payload["fuel_km"]) if payload.get("fuel_km") not in (None, "") else None
        fuel_cost = float(payload["fuel_cost"]) if payload.get("fuel_cost") not in (None, "") else None
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date or number")
    worker = await _resolve_worker(user["user_id"], payload.get("worker_id"), user)
    job_snap = await _job_snapshot(payload.get("job_id"), user["user_id"])
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "entry_id": f"te_{uuid.uuid4().hex[:12]}",
        "provider_id": user["user_id"],
        **worker,
        **job_snap,
        "type": entry_type,
        "mode": (payload.get("mode") or "manual").lower(),
        "started_at": payload["started_at"],
        "ended_at": payload["ended_at"],
        "started_lat": payload.get("start_lat"),
        "started_lng": payload.get("start_lng"),
        "ended_lat": payload.get("end_lat"),
        "ended_lng": payload.get("end_lng"),
        "notes": (payload.get("notes") or "").strip() or None,
        "fuel_km": fuel_km,
        "fuel_cost": fuel_cost,
        "hourly_rate_snapshot": float(payload.get("hourly_rate") or worker["hourly_rate"]),
        "billable": bool(payload.get("billable", True)),
        "created_at": now,
    }
    await db.time_entries.insert_one(entry.copy())
    return _serialize_entry(entry)


@api.patch("/timesheets/entries/{entry_id}")
async def timesheets_update(entry_id: str, payload: Dict[str, Any], user=Depends(require_user)):
    entry = await db.time_entries.find_one({"entry_id": entry_id})
    if not entry or entry.get("provider_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="Entry not found")
    allowed = {k: payload[k] for k in ("notes", "billable", "fuel_km", "fuel_cost", "started_at", "ended_at", "hourly_rate_snapshot", "type") if k in payload}
    if "type" in allowed and allowed["type"] not in TIME_ENTRY_TYPES:
        raise HTTPException(status_code=400, detail="invalid type")
    await db.time_entries.update_one({"entry_id": entry_id}, {"$set": allowed})
    entry.update(allowed)
    return _serialize_entry(entry)


@api.delete("/timesheets/entries/{entry_id}")
async def timesheets_delete(entry_id: str, user=Depends(require_user)):
    entry = await db.time_entries.find_one({"entry_id": entry_id}, {"_id": 1, "provider_id": 1})
    if not entry or entry.get("provider_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.time_entries.delete_one({"entry_id": entry_id})
    return {"ok": True}


@api.get("/timesheets/summary")
async def timesheets_summary(
    job_id: Optional[str] = None,
    worker_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user=Depends(require_user),
):
    """Aggregate totals broken down by type + billable. Used by invoice + dashboard."""
    if user["role"] != "provider":
        raise HTTPException(status_code=403, detail="Provider role required")
    query: Dict[str, Any] = {"provider_id": user["user_id"]}
    if job_id:
        query["job_id"] = job_id
    if worker_id:
        query["worker_id"] = worker_id
    if date_from or date_to:
        rng: Dict[str, Any] = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        query["started_at"] = rng
    entries = await db.time_entries.find(query, {"_id": 0}).to_list(5000)
    buckets = {"work": {"minutes": 0.0, "cost": 0.0, "count": 0}, "travel": {"minutes": 0.0, "cost": 0.0, "count": 0}, "materials": {"minutes": 0.0, "cost": 0.0, "count": 0}}
    total_minutes = 0.0
    total_cost = 0.0
    billable_cost = 0.0
    fuel_cost = 0.0
    for e in entries:
        mins = _entry_duration_seconds(e) / 60.0
        cost = _entry_billable_cost(e)
        t = e.get("type", "work")
        if t not in buckets:
            buckets[t] = {"minutes": 0.0, "cost": 0.0, "count": 0}
        buckets[t]["minutes"] += mins
        buckets[t]["cost"] += cost
        buckets[t]["count"] += 1
        total_minutes += mins
        total_cost += cost
        if e.get("billable", True):
            billable_cost += cost
        if e.get("fuel_cost"):
            fuel_cost += float(e["fuel_cost"])
    for b in buckets.values():
        b["minutes"] = round(b["minutes"], 2)
        b["hours"] = round(b["minutes"] / 60.0, 2)
        b["cost"] = round(b["cost"], 2)
    return {
        "entries": len(entries),
        "total_minutes": round(total_minutes, 2),
        "total_hours": round(total_minutes / 60.0, 2),
        "total_cost": round(total_cost, 2),
        "billable_cost": round(billable_cost, 2),
        "fuel_cost": round(fuel_cost, 2),
        "by_type": buckets,
    }


@api.get("/timesheets/jobs")
async def timesheets_jobs(user=Depends(require_user)):
    """Jobs a provider can log time against: booked jobs + accepted bids."""
    if user["role"] != "provider":
        raise HTTPException(status_code=403, detail="Provider role required")
    uid = user["user_id"]
    bookings = await db.bookings.find({"provider_id": uid, "job_id": {"$ne": None}}, {"_id": 0, "job_id": 1}).to_list(500)
    bids = await db.bids.find({"provider_id": uid, "status": {"$in": ["accepted", "completed"]}}, {"_id": 0, "job_id": 1}).to_list(500)
    job_ids = list({x["job_id"] for x in bookings + bids if x.get("job_id")})
    if not job_ids:
        return []
    return await db.jobs.find({"job_id": {"$in": job_ids}}, {"_id": 0}).sort("created_at", -1).to_list(500)


GST_RATE = 0.15
TYPE_LINE_LABEL = {"work": "Labour", "travel": "Travel time", "materials": "Materials pickup"}


@api.get("/jobs/{job_id}/invoice")
async def job_invoice(job_id: str, user=Depends(require_user)):
    job, provider_id = await _invoice_context(job_id, user)
    inv = await _compute_invoice(job, provider_id)
    sent = await db.invoices.find_one({"job_id": job_id}, {"_id": 0})
    # Customers see the last version the provider sent; providers see the live draft.
    if sent and user["user_id"] != provider_id:
        return {**sent, "is_sent_copy": True, "sent": _sent_meta(sent)}
    return {**inv, "is_sent_copy": False, "sent": _sent_meta(sent) if sent else None,
            "payment_status": (sent or {}).get("payment_status", "unpaid")}


def _sent_meta(s: Dict[str, Any]) -> Dict[str, Any]:
    return {"version": s.get("version"), "sent_at": s.get("sent_at"), "total": s.get("total"), "email_sent": s.get("email_sent")}


async def _invoice_context(job_id: str, user: Dict[str, Any]):
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    bid = await db.bids.find_one({"job_id": job_id, "status": {"$in": ["accepted", "completed"]}}, {"_id": 0})
    provider_id = (bid or {}).get("provider_id")
    if not provider_id:
        booking = await db.bookings.find_one({"job_id": job_id}, {"_id": 0})
        provider_id = (booking or {}).get("provider_id")
    allowed = {job.get("client_id"), job.get("approver_id"), provider_id} - {None}
    if user["user_id"] not in allowed:
        raise HTTPException(status_code=403, detail="Not allowed")
    return job, provider_id


async def _compute_invoice(job: Dict[str, Any], provider_id: Optional[str]) -> Dict[str, Any]:
    """Invoice = agreed quote + billable timesheet line items for the job."""
    job_id = job["job_id"]
    bid = await db.bids.find_one({"job_id": job_id, "status": {"$in": ["accepted", "completed"]}}, {"_id": 0})
    entries = await db.time_entries.find(
        {"job_id": job_id, "provider_id": provider_id, "billable": True, "ended_at": {"$ne": None}}, {"_id": 0}
    ).sort("started_at", 1).to_list(1000)
    lines: List[Dict[str, Any]] = []
    if bid:
        lines.append({"kind": "quote", "description": f"Agreed quote — {bid.get('provider_name') or 'provider'}", "quantity": 1, "unit": "fixed", "rate": float(bid["amount"]), "amount": round(float(bid["amount"]), 2)})
    groups: Dict[tuple, Dict[str, Any]] = {}
    fuel_total = 0.0
    fuel_km = 0.0
    for e in entries:
        mins = _entry_duration_seconds(e) / 60.0
        rate = float(e.get("hourly_rate_snapshot") or 0)
        key = (e.get("type", "work"), e.get("worker_name"), rate)
        g = groups.setdefault(key, {"minutes": 0.0, "amount": 0.0})
        g["minutes"] += mins
        g["amount"] += mins * rate / 60.0
        fuel_total += float(e.get("fuel_cost") or 0)
        fuel_km += float(e.get("fuel_km") or 0)
    for (t, worker, rate), g in groups.items():
        lines.append({"kind": t, "description": f"{TYPE_LINE_LABEL.get(t, t.title())} — {worker}", "quantity": round(g["minutes"] / 60.0, 2), "unit": "hours", "rate": rate, "amount": round(g["amount"], 2)})
    if fuel_total:
        lines.append({"kind": "fuel", "description": f"Fuel / vehicle{f' ({round(fuel_km, 1)} km)' if fuel_km else ''}", "quantity": 1, "unit": "fixed", "rate": round(fuel_total, 2), "amount": round(fuel_total, 2)})
    # Receipts the provider attached to this job (materials, hire, third-party…) — billed ex-GST, GST added below
    for r in await db.receipts.find({"job_id": job_id, "provider_id": provider_id}, {"_id": 0}).sort("created_at", 1).to_list(200):
        ex = round(r["total"] - r["gst"], 2) if r.get("gst") is not None else round(r["total"] / (1 + GST_RATE), 2)
        name = {"materials": "Materials", "equipment_purchase": "Equipment purchase", "equipment_hire": "Equipment hire",
                "third_party": "Third-party service", "travel": "Travel", "fuel": "Fuel"}.get(r["cost_type"], "Expense")
        lines.append({"kind": f"receipt_{r['cost_type']}", "description": f"{name} — {r.get('supplier') or 'receipt'}", "quantity": 1,
                      "unit": "receipt", "rate": ex, "amount": ex, "receipt_id": r["receipt_id"]})
    subtotal = round(sum(line["amount"] for line in lines), 2)
    gst = round(subtotal * GST_RATE, 2)
    return {
        "job_id": job_id,
        "job_title": job.get("title"),
        "job_status": job.get("status"),
        "provider_id": provider_id,
        "lines": lines,
        "timesheet_minutes": round(sum(g["minutes"] for g in groups.values()), 2),
        "entries_count": len(entries),
        "subtotal": subtotal,
        "gst_rate": GST_RATE,
        "gst": gst,
        "total": round(subtotal + gst, 2),
    }


def _invoice_email_html(inv: Dict[str, Any], client_name: str, provider_name: str, app_url: str) -> str:
    rows = "".join(
        f'<tr><td style="padding:8px 0;border-bottom:1px solid #eee">{escape(str(line["description"]))}</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid #eee;text-align:right">${line["amount"]:.2f}</td></tr>'
        for line in inv["lines"]
    )
    link = f'<p><a href="{escape(app_url)}/jobs/{escape(inv["job_id"])}" style="color:#3b82f6">View the job and invoice in {escape(EMAIL_FROM_NAME)}</a></p>' if app_url.startswith("https://") else ""
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#111">'
        f'<h2 style="margin:0 0 8px">Invoice for {escape(inv.get("job_title") or "your job")}</h2>'
        f'<p>Hi {escape(client_name)}, {escape(provider_name)} has sent you an invoice (version {inv["version"]}).</p>'
        f'<table role="presentation" width="100%" style="font-size:14px">{rows}'
        f'<tr><td style="padding:8px 0">Subtotal</td><td style="text-align:right">${inv["subtotal"]:.2f}</td></tr>'
        f'<tr><td style="padding:4px 0">GST ({int(inv["gst_rate"] * 100)}%)</td><td style="text-align:right">${inv["gst"]:.2f}</td></tr>'
        f'<tr><td style="padding:8px 0;font-weight:bold">Total</td><td style="text-align:right;font-weight:bold">${inv["total"]:.2f}</td></tr></table>'
        f'{link}'
        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password or card details by email.</p>'
        '</td></tr></table>'
    )


@api.post("/jobs/{job_id}/invoice/send")
async def send_job_invoice(job_id: str, request: Request, user=Depends(require_user)):
    if await db.payment_transactions.find_one({"job_id": job_id, "payment_status": "paid"}):
        raise HTTPException(status_code=400, detail="This invoice has already been paid")
    job, provider_id = await _invoice_context(job_id, user)
    if user["user_id"] != provider_id:
        raise HTTPException(status_code=403, detail="Only the job's provider can send the invoice")
    inv = await _compute_invoice(job, provider_id)
    if not inv["lines"]:
        raise HTTPException(status_code=400, detail="Nothing to invoice yet")
    prev = await db.invoices.find_one({"job_id": job_id}, {"_id": 0, "version": 1, "invoice_id": 1})
    now = datetime.now(timezone.utc).isoformat()
    inv.update({
        "invoice_id": (prev or {}).get("invoice_id") or f"inv_{uuid.uuid4().hex[:10]}",
        "version": ((prev or {}).get("version") or 0) + 1,
        "client_id": job.get("client_id"),
        "provider_name": user.get("name"),
        "sent_at": now,
        "status": "sent",
    })
    client = await db.users.find_one({"user_id": job.get("client_id")}, {"_id": 0, "password_hash": 0}) or {}
    # Chat message in the provider <-> customer thread
    thread = await db.threads.find_one({"participants": {"$all": [provider_id, job.get("client_id")]}}, {"_id": 0})
    if not thread:
        thread = Thread(
            participants=[provider_id, job.get("client_id")],
            participant_names={provider_id: user["name"], job.get("client_id"): client.get("name", "Customer")},
            subject=job.get("title") or "Job",
        ).dict()
        await db.threads.insert_one(thread)
    verb = "an updated invoice" if inv["version"] > 1 else "an invoice"
    content = f"I've sent {verb} for \"{job.get('title')}\": ${inv['total']:.2f} incl. GST. Open the job to see the full breakdown."
    msg = Message(thread_id=thread["thread_id"], sender_id=provider_id, content=content)
    await db.messages.insert_one(msg.dict())
    await db.threads.update_one({"thread_id": thread["thread_id"]}, {"$set": {"last_message": content, "last_message_at": msg.timestamp}})
    # Email copy (non-fatal if it fails)
    inv["email_sent"] = False
    if client.get("email"):
        try:
            origin = request.headers.get("origin") or ""
            html = _invoice_email_html(inv, client.get("name", "there"), user.get("name", "Your provider"), origin)
            await send_email(to=client["email"], subject=f"Invoice for {job.get('title')} — ${inv['total']:.2f}", html=html)
            inv["email_sent"] = True
        except HTTPException as e:
            logger.warning(f"Invoice email not sent for {job_id}: {e.detail}")
    await db.invoices.update_one({"job_id": job_id}, {"$set": inv}, upsert=True)
    inv.pop("_id", None)
    return {**inv, "sent": _sent_meta(inv), "is_sent_copy": False, "thread_id": thread["thread_id"]}


# ---------------- MEDIA UPLOADS (chunked → object storage) ----------------
UPLOAD_TMP = Path("/tmp/pf_uploads")
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_VIDEO_BYTES = 200 * 1024 * 1024
MAX_CHUNK_BYTES = 6 * 1024 * 1024


class UploadInit(BaseModel):
    filename: str
    content_type: str
    size: int


@api.post("/uploads/init")
async def upload_init(payload: UploadInit, user=Depends(require_user)):
    ct = (payload.content_type or "").lower()
    if not (ct.startswith("image/") or ct.startswith("video/") or ct == "application/pdf"):
        raise HTTPException(status_code=400, detail="Only photos, videos and PDF documents can be uploaded")
    limit = MAX_VIDEO_BYTES if ct.startswith("video/") else MAX_IMAGE_BYTES
    if payload.size <= 0 or payload.size > limit:
        raise HTTPException(status_code=400, detail=f"File too large (max {limit // (1024 * 1024)} MB)")
    upload_id = f"up_{uuid.uuid4().hex[:16]}"
    (UPLOAD_TMP / upload_id).mkdir(parents=True, exist_ok=True)
    await db.uploads.insert_one({"upload_id": upload_id, "user_id": user["user_id"], "filename": payload.filename[:200],
                                 "content_type": ct, "size": payload.size, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"upload_id": upload_id, "chunk_size": 5 * 1024 * 1024}


async def _own_upload(upload_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    up = await db.uploads.find_one({"upload_id": upload_id, "user_id": user["user_id"]}, {"_id": 0})
    if not up:
        raise HTTPException(status_code=404, detail="Upload not found")
    return up


@api.put("/uploads/{upload_id}/chunk")
async def upload_chunk(upload_id: str, index: int, request: Request, user=Depends(require_user)):
    await _own_upload(upload_id, user)
    data = await request.body()
    if not data or len(data) > MAX_CHUNK_BYTES or index < 0 or index > 1000:
        raise HTTPException(status_code=400, detail="Invalid chunk")
    (UPLOAD_TMP / upload_id / f"{index:05d}").write_bytes(data)
    return {"ok": True, "index": index}


@api.post("/uploads/{upload_id}/complete")
async def upload_complete(upload_id: str, total_chunks: int, user=Depends(require_user)):
    import asyncio
    import re as _re
    import shutil
    up = await _own_upload(upload_id, user)
    folder = UPLOAD_TMP / upload_id
    parts = [folder / f"{i:05d}" for i in range(total_chunks)]
    if total_chunks <= 0 or not all(p.exists() for p in parts):
        raise HTTPException(status_code=400, detail="Missing chunks — please retry the upload")
    data = b"".join(p.read_bytes() for p in parts)
    if len(data) != up["size"]:
        raise HTTPException(status_code=400, detail="Upload incomplete — please retry")
    ext = up["filename"].rsplit(".", 1)[-1].lower() if "." in up["filename"] else up["content_type"].split("/")[-1]
    ext = _re.sub(r"[^a-z0-9]", "", ext)[:8] or "bin"
    path = f"{APP_NAME}/uploads/{user['user_id']}/{uuid.uuid4()}.{ext}"
    try:
        result = await asyncio.to_thread(put_object, path, data, up["content_type"])
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(status_code=502, detail="Could not store the file, please try again")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    file_id = f"file_{uuid.uuid4().hex[:16]}"
    safe_name = _re.sub(r"[^A-Za-z0-9._-]", "_", up["filename"])[:80] or f"file.{ext}"
    await db.files.insert_one({"file_id": file_id, "storage_path": result["path"], "original_filename": up["filename"],
                               "content_type": up["content_type"], "size": len(data), "owner_id": user["user_id"],
                               "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
    await db.uploads.delete_one({"upload_id": upload_id})
    return {"file_id": file_id, "url": f"/api/files/{file_id}/{safe_name}", "content_type": up["content_type"], "name": up["filename"], "size": len(data)}


@api.get("/files/{file_id}/{filename}")
async def get_file(file_id: str, filename: str, request: Request, user=Depends(require_user)):
    import asyncio
    rec = await db.files.find_one({"file_id": file_id, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    # Provider credential files (police checks, qualifications) are private: owner + reviewers only
    if rec.get("owner_id") != user["user_id"] and not is_reviewer(user):
        if await db.provider_documents.find_one({"file_url": {"$regex": f"^/api/files/{file_id}/"}}, {"_id": 1}):
            raise HTTPException(status_code=404, detail="File not found")
    data, _ = await asyncio.to_thread(get_object, rec["storage_path"])
    headers = {"Cache-Control": "private, max-age=86400", "Accept-Ranges": "bytes"}
    rng = request.headers.get("range")
    if rng and rng.startswith("bytes="):
        # Byte ranges so phone browsers (iOS Safari) can stream videos
        start_s, _, end_s = rng[6:].split(",")[0].partition("-")
        size = len(data)
        start = int(start_s) if start_s else max(0, size - int(end_s or 0))
        end = min(int(end_s), size - 1) if (end_s and start_s) else size - 1
        if start >= size or start > end:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        return Response(content=data[start:end + 1], status_code=206, media_type=rec["content_type"], headers=headers)
    return Response(content=data, media_type=rec["content_type"], headers=headers)


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
    if not items:
        return []
    # Batch-fetch counterparties to avoid N+1 (previously 1 query per tenancy).
    user_ids = set()
    for t in items:
        if t.get("tenant_id"):
            user_ids.add(t["tenant_id"])
        if t.get("approver_id"):
            user_ids.add(t["approver_id"])
    umap: Dict[str, Dict[str, Any]] = {}
    if user_ids:
        users_list = await db.users.find(
            {"user_id": {"$in": list(user_ids)}},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1},
        ).to_list(len(user_ids))
        umap = {u["user_id"]: u for u in users_list}
    out = []
    for t in items:
        tenant_full = umap.get(t.get("tenant_id"))
        tenant = None
        if tenant_full:
            tenant = {k: tenant_full[k] for k in ("user_id", "name", "email") if k in tenant_full}
        approver = umap.get(t.get("approver_id")) if t.get("approver_id") else None
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
    if not updated.get("assigned_provider_id"):
        await dispatch_job(updated)
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


# ---------------- SERVICES TAXONOMY (Residential + Commercial tracks) ----------------
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
    {"id": "commercial-cleaning", "name": "Commercial Cleaning & Facility Hygiene", "icon": "SprayCan", "color": "#06B6D4", "subs": [
        "Office Cleaning", "Retail Cleaning", "Medical & Healthcare Cleaning", "Industrial & Warehouse Cleaning",
        "School & Childcare Cleaning", "Commercial Window Cleaning", "High-Rise Window Cleaning",
        "Carpet & Hard Floor Care", "Builders' Clean", "Commercial Water Blasting",
        "Washroom Hygiene Services", "Body Corporate Cleaning", "Commercial Kitchen & Hood Cleaning",
    ]},
    {"id": "grounds-maintenance", "name": "Gardening & Grounds Maintenance", "icon": "Flower2", "color": "#22C55E", "subs": [
        "Commercial Lawn Mowing", "Grounds Maintenance Contracts", "Hedge & Shrub Maintenance",
        "Tree Care & Arborist", "Weed Control & Spraying", "Commercial Green Waste Removal",
        "Irrigation Maintenance", "Interior Plant Care",
    ]},
    {"id": "commercial-landscaping", "name": "Landscaping", "icon": "Trees", "color": "#15803D", "subs": [
        "Commercial Landscape Design", "Commercial Landscape Construction", "Paving & Hardscaping",
        "Car Park Landscaping", "Commercial Retaining Walls", "Commercial Artificial Turf",
        "Outdoor & Amenity Lighting", "Stormwater & Drainage",
    ]},
]

RESIDENTIAL_TAXONOMY = [
    {"id": "general-home-maintenance", "name": "General Home Maintenance", "icon": "Home", "color": "#3B82F6", "subs": [
        "Handyman Services", "Home Repairs", "Property Maintenance", "Preventative Maintenance", "Odd Jobs",
        "Home Improvements",
    ]},
    {"id": "electrical", "name": "Electrical", "icon": "Zap", "color": "#F59E0B", "subs": [
        "Residential Electrical", "New Wiring & Rewiring", "Lighting Installation", "Power Points & Switches",
        "Switchboard Upgrades", "EV Charger Installation", "Smoke Alarms", "Fault Finding & Repairs",
    ]},
    {"id": "plumbing-gas", "name": "Plumbing & Gas", "icon": "Droplets", "color": "#0EA5E9", "subs": [
        "Residential Plumbing", "Blocked Drains", "Leak Repairs", "Hot Water Systems", "Tap & Toilet Repairs",
        "Bathroom Plumbing", "Kitchen Plumbing", "Gas Fitting & Gas Appliances",
    ]},
    {"id": "heating-cooling-ventilation", "name": "Heating, Cooling & Ventilation", "icon": "Wind", "color": "#06B6D4", "subs": [
        "Heat Pump Installation", "Air Conditioning", "Home Ventilation Systems", "Bathroom Extractor Fans",
        "Ducted Heating", "HVAC Servicing",
    ]},
    {"id": "roofing-guttering", "name": "Roofing & Guttering", "icon": "Home", "color": "#EF4444", "subs": [
        "Roof Repairs", "Roof Replacement", "Gutter Repairs", "Gutter Replacement", "Downpipes",
        "Roof Leak Repairs", "Skylight Installation",
    ]},
    {"id": "carpentry-joinery", "name": "Carpentry & Joinery", "icon": "Hammer", "color": "#A16207", "subs": [
        "General Carpentry", "Deck Construction", "Pergolas", "Fencing", "Doors", "Windows", "Built-in Cabinets",
        "Kitchen Cabinetry", "Gates",
    ]},
    {"id": "painting-interior-finishes", "name": "Painting & Interior Finishes", "icon": "Paintbrush", "color": "#EC4899", "subs": [
        "Interior Painting", "Exterior Painting", "Gib Installation", "Gib Stopping", "Plastering",
        "Wallpaper Installation", "Ceiling Repairs",
    ]},
    {"id": "flooring-tiling", "name": "Flooring & Tiling", "icon": "Grid3x3", "color": "#F97316", "subs": [
        "Timber Flooring", "Laminate Flooring", "Vinyl Flooring", "Carpet Installation", "Floor Repairs",
        "Floor & Wall Tiling", "Bathroom Tiling", "Kitchen Splashbacks",
    ]},
    {"id": "kitchens-bathrooms-renovations", "name": "Kitchens, Bathrooms & Renovations", "icon": "Sparkles", "color": "#8B5CF6", "subs": [
        "Kitchen Renovations", "Bathroom Renovations", "Laundry Renovations", "Home Alterations", "Room Additions",
        "Home Extensions", "Interior Refurbishments", "Builders & Renovations",
    ]},
    {"id": "concrete-outdoor-construction", "name": "Concrete & Outdoor Construction", "icon": "Layers", "color": "#71717A", "subs": [
        "Driveways", "Paths", "Concrete Slabs", "Retaining Walls", "Paving", "Excavation", "Site Preparation",
        "Bricklaying & Masonry",
    ]},
    {"id": "glass-windows", "name": "Glass & Windows", "icon": "Square", "color": "#0891B2", "subs": [
        "Glass Replacement", "Double Glazing", "Window Installation", "Shower Glass", "Mirrors",
        "Glass Balustrades",
    ]},
    {"id": "security-smart-home", "name": "Security & Smart Home", "icon": "ShieldCheck", "color": "#7C3AED", "subs": [
        "CCTV Installation", "Alarm Systems", "Smart Doorbells", "Smart Locks", "Intercom Systems",
        "Access Control", "Home Automation", "Locksmith Services",
    ]},
    {"id": "data-communications", "name": "Home IT, Data & Communications", "icon": "Router", "color": "#2563EB", "subs": [
        "Wi-Fi Installation", "Data Cabling", "Fibre Cabling", "TV Wall Mounting", "Home Networking",
        "Audio & Visual Installation", "Home IT Support",
    ]},
    {"id": "solar-energy", "name": "Solar & Energy", "icon": "Sun", "color": "#10B981", "subs": [
        "Solar Panel Installation", "Home Battery Installation", "EV Chargers", "Energy Monitoring",
        "Backup Power Systems", "Solar Maintenance",
    ]},
    {"id": "pools-spas-outdoor-living", "name": "Pools, Spas & Outdoor Living", "icon": "Waves", "color": "#0EA5E9", "subs": [
        "Swimming Pool Installation", "Spa Pool Installation", "Pool Pumps & Filtration", "Outdoor Kitchens",
        "Outdoor Lighting", "Shade Structures",
    ]},
    {"id": "insulation-weatherproofing", "name": "Insulation & Weatherproofing", "icon": "Thermometer", "color": "#65A30D", "subs": [
        "Ceiling Insulation", "Underfloor Insulation", "Wall Insulation", "Moisture Barriers", "Home Ventilation",
        "Weatherproofing",
    ]},
    {"id": "appliance-installation", "name": "Appliance Installation & Repairs", "icon": "Refrigerator", "color": "#F59E0B", "subs": [
        "Ovens & Cooktops", "Dishwashers", "Rangehoods", "Washing Machines", "Dryers", "Waste Disposals",
        "Water Filters", "Appliance Repairs",
    ]},
    {"id": "specialist-home-services", "name": "Specialist Home Services", "icon": "HardHat", "color": "#DC2626", "subs": [
        "Waterproofing", "Asbestos Removal (Licensed)", "Demolition", "Structural Repairs",
        "Welding & Metal Fabrication", "Accessibility Modifications",
    ]},
    {"id": "gardening-lawn", "name": "Gardening & Lawn", "icon": "Flower2", "color": "#22C55E", "subs": [
        "Lawn Mowing", "Lawn Care & Fertilising", "New Lawns & Turf Laying", "Garden Maintenance",
        "Weeding & Mulching", "Hedge Trimming", "Pruning", "Tree Felling & Removal", "Stump Grinding",
        "Planting & Garden Makeovers", "Green Waste Removal", "Garden Irrigation", "Arborist & Tree Services",
    ]},
    {"id": "landscaping", "name": "Landscaping", "icon": "Trees", "color": "#15803D", "subs": [
        "Landscape Design", "Landscape Construction", "Garden Beds & Edging", "Paving & Pathways",
        "Landscape Retaining Walls", "Outdoor Living Areas", "Artificial Turf", "Water Features",
        "Garden Lighting", "Section Drainage", "Section Clearing",
    ]},
    {"id": "cleaning", "name": "Cleaning & Home Hygiene", "icon": "SprayCan", "color": "#06B6D4", "subs": [
        "Regular House Cleaning", "Deep Cleaning", "End of Tenancy Cleaning", "Move In / Move Out Cleaning",
        "Carpet Cleaning", "Upholstery Cleaning", "Window Cleaning", "Oven Cleaning", "Water Blasting",
        "House Washing", "Gutter Cleaning", "Roof Cleaning & Moss Treatment", "After-Builders Cleaning",
        "Mould Removal", "Pest Control", "Chimney & Duct Cleaning",
    ]},
    {"id": "building-engineering-inspections", "name": "Building Engineering & Inspections", "icon": "ClipboardCheck", "color": "#0F766E", "subs": [
        "Building & Property Inspections", "Building Service Engineering", "Architecture & Drafting",
    ]},
    {"id": "moving-delivery-rubbish", "name": "Moving, Delivery & Rubbish Removal", "icon": "Truck", "color": "#B45309", "subs": [
        "Rubbish & Green Waste Removal", "Man with a Van / Local Movers", "Full-Service House Removals",
    ]},
    {"id": "home-care-pet-services", "name": "Home Care, Elderly Support & Pet Services", "icon": "HeartHandshake", "color": "#DB2777", "subs": [
        "Elderly & Independent Living Support", "Pet Care & Grooming",
    ]},
    {"id": "tutoring-advisory-professional", "name": "In-Home Tutoring, Advisory & Professional Services", "icon": "GraduationCap", "color": "#4F46E5", "subs": [
        "In-Home Tutoring & Music Lessons", "Insurance & Mortgage Advisory", "Personal Tech & Admin Coaching",
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


RESIDENTIAL_TAXONOMY_INDEX = _index_taxonomy(RESIDENTIAL_TAXONOMY)
COMMERCIAL_TAXONOMY_INDEX = _index_taxonomy(COMMERCIAL_TAXONOMY)


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


# (keywords, residential sub, commercial sub or None) — drives free-text job type detection
SERVICE_KEYWORDS: List[tuple] = [
    (['tap', 'faucet', 'dripping'], 'Tap & Toilet Repairs', 'Commercial Plumbing'),
    (['toilet', 'cistern', 'loo'], 'Tap & Toilet Repairs', 'Bathrooms & Amenities'),
    (['leak', 'leaking', 'burst pipe', 'water leak'], 'Leak Repairs', 'Pipework'),
    (['drain', 'blocked', 'blockage', 'clogged', 'sewer'], 'Blocked Drains', 'Drain Repairs'),
    (['hot water', 'cylinder', 'califont'], 'Hot Water Systems', 'Hot Water Systems'),
    (['gas', 'gas fitting', 'gas bottle', 'gas hob'], 'Gas Fitting & Gas Appliances', 'Gas Fitting'),
    (['plumber', 'plumbing', 'pipe'], 'Residential Plumbing', 'Commercial Plumbing'),
    (['electrician', 'sparky', 'wiring', 'rewire'], 'New Wiring & Rewiring', 'Commercial Electrical'),
    (['power point', 'socket', 'switch', 'outlet'], 'Power Points & Switches', 'Power & Data'),
    (['light', 'lights', 'lighting', 'downlight', 'led'], 'Lighting Installation', 'Lighting Installation & Upgrades'),
    (['switchboard', 'fuse'], 'Switchboard Upgrades', 'Switchboard Upgrades'),
    (['ev charger', 'car charger'], 'EV Charger Installation', 'EV Charger Installation'),
    (['smoke alarm'], 'Smoke Alarms', 'Fire Alarms'),
    (['tripping', 'no power', 'power out', 'electrical fault'], 'Fault Finding & Repairs', 'Electrical Fault Finding'),
    (['heat pump', 'heatpump'], 'Heat Pump Installation', 'Heat Pumps'),
    (['air con', 'aircon', 'air conditioning', 'air conditioner'], 'Air Conditioning', 'Commercial Air Conditioning'),
    (['extractor', 'ventilation', 'condensation'], 'Bathroom Extractor Fans', 'Ventilation Systems'),
    (['roof', 'roofer', 'roofing', 'tiles cracked'], 'Roof Repairs', 'Roof Repairs'),
    (['gutter', 'gutters', 'spouting', 'downpipe'], 'Gutter Repairs', 'Gutters & Downpipes'),
    (['deck', 'decking'], 'Deck Construction', 'Commercial Carpentry'),
    (['fence', 'fencing'], 'Fencing', 'Fencing & Gates'),
    (['pergola'], 'Pergolas', 'Commercial Carpentry'),
    (['door', 'doors'], 'Doors', 'Doors & Hardware'),
    (['cabinet', 'cabinetry', 'joinery'], 'Built-in Cabinets', 'Cabinetry'),
    (['carpenter', 'builder', 'carpentry'], 'General Carpentry', 'Commercial Carpentry'),
    (['paint', 'painter', 'painting', 'repaint'], 'Interior Painting', 'Painting'),
    (['exterior paint', 'paint the house', 'outside of the house'], 'Exterior Painting', 'Painting'),
    (['gib', 'plasterboard'], 'Gib Installation', 'Gib Installation'),
    (['plaster', 'plastering'], 'Plastering', 'Plastering'),
    (['wallpaper'], 'Wallpaper Installation', 'Painting'),
    (['carpet laying', 'new carpet'], 'Carpet Installation', 'Flooring'),
    (['tile', 'tiles', 'tiling', 'tiler'], 'Floor & Wall Tiling', 'Tiling'),
    (['floor', 'flooring', 'floorboards', 'laminate', 'vinyl'], 'Floor Repairs', 'Flooring'),
    (['kitchen renovation', 'new kitchen', 'kitchen reno'], 'Kitchen Renovations', 'Hospitality Fit-outs'),
    (['bathroom renovation', 'bathroom reno', 'new bathroom'], 'Bathroom Renovations', 'Bathrooms & Amenities'),
    (['renovation', 'extension', 'alteration'], 'Home Alterations', 'Office Renovations'),
    (['driveway', 'concrete'], 'Driveways', 'Concrete Repairs'),
    (['excavation', 'digger'], 'Excavation', 'Concrete Repairs'),
    (['window', 'glass', 'glazing', 'double glazing'], 'Glass Replacement', 'Glass Replacement'),
    (['cctv', 'security camera', 'camera'], 'CCTV Installation', 'CCTV Installation'),
    (['alarm', 'burglar'], 'Alarm Systems', 'Alarm Systems'),
    (['wifi', 'wi-fi', 'internet', 'network'], 'Wi-Fi Installation', 'Wi-Fi Installation'),
    (['tv mount', 'mount tv', 'tv on the wall'], 'TV Wall Mounting', 'Communications Infrastructure'),
    (['solar', 'solar panel'], 'Solar Panel Installation', 'Commercial Solar'),
    (['battery'], 'Home Battery Installation', 'Battery Storage'),
    (['pool', 'swimming pool'], 'Swimming Pool Installation', 'Building Upgrades'),
    (['spa', 'hot tub'], 'Spa Pool Installation', 'Building Upgrades'),
    (['insulation', 'insulate'], 'Ceiling Insulation', 'Building Upgrades'),
    (['dishwasher'], 'Dishwashers', 'Kitchens'),
    (['oven install', 'cooktop', 'hob'], 'Ovens & Cooktops', 'Kitchens'),
    (['washing machine'], 'Washing Machines', 'Commercial Plumbing'),
    (['rangehood'], 'Rangehoods', 'Extraction Systems'),
    (['asbestos'], 'Asbestos Removal (Licensed)', 'Building Repairs'),
    (['demolition', 'demolish'], 'Demolition', 'Building Alterations'),
    (['welding', 'welder', 'metal'], 'Welding & Metal Fabrication', 'Building Repairs'),
    (['handyman', 'odd jobs', 'fix', 'repair', 'broken'], 'Handyman Services', 'Commercial Handyman'),
    (['mow', 'mowing', 'lawn', 'grass', 'lawns'], 'Lawn Mowing', 'Commercial Lawn Mowing'),
    (['fertilise', 'fertilize', 'lawn care', 'patchy lawn'], 'Lawn Care & Fertilising', 'Grounds Maintenance Contracts'),
    (['turf', 'new lawn', 'lawn seed', 're-sow'], 'New Lawns & Turf Laying', 'Grounds Maintenance Contracts'),
    (['garden', 'gardener', 'gardening', 'tidy up'], 'Garden Maintenance', 'Grounds Maintenance Contracts'),
    (['weed', 'weeds', 'weeding', 'mulch', 'bark'], 'Weeding & Mulching', 'Weed Control & Spraying'),
    (['hedge', 'hedges'], 'Hedge Trimming', 'Hedge & Shrub Maintenance'),
    (['prune', 'pruning', 'shrub'], 'Pruning', 'Hedge & Shrub Maintenance'),
    (['tree', 'trees', 'arborist', 'felling'], 'Tree Felling & Removal', 'Tree Care & Arborist'),
    (['stump'], 'Stump Grinding', 'Tree Care & Arborist'),
    (['planting', 'plants', 'flower', 'flowers', 'vege garden'], 'Planting & Garden Makeovers', 'Interior Plant Care'),
    (['green waste', 'garden waste', 'rubbish'], 'Green Waste Removal', 'Commercial Green Waste Removal'),
    (['irrigation', 'sprinkler', 'watering'], 'Garden Irrigation', 'Irrigation Maintenance'),
    (['landscape', 'landscaping', 'landscaper'], 'Landscape Design', 'Commercial Landscape Design'),
    (['garden bed', 'edging', 'raised bed'], 'Garden Beds & Edging', 'Commercial Landscape Construction'),
    (['paving', 'pavers', 'path', 'pathway'], 'Paving & Pathways', 'Paving & Hardscaping'),
    (['retaining wall'], 'Landscape Retaining Walls', 'Commercial Retaining Walls'),
    (['patio', 'courtyard', 'outdoor area'], 'Outdoor Living Areas', 'Commercial Landscape Construction'),
    (['artificial turf', 'artificial grass', 'fake grass'], 'Artificial Turf', 'Commercial Artificial Turf'),
    (['water feature', 'pond', 'fountain'], 'Water Features', 'Commercial Landscape Construction'),
    (['garden lighting', 'outdoor lighting'], 'Garden Lighting', 'Outdoor & Amenity Lighting'),
    (['drainage', 'soggy', 'waterlogged', 'stormwater'], 'Section Drainage', 'Stormwater & Drainage'),
    (['section clearing', 'clear the section', 'overgrown', 'dirt', 'earth'], 'Section Clearing', 'Commercial Landscape Construction'),
    (['clean', 'cleaner', 'cleaning', 'housekeeping'], 'Regular House Cleaning', 'Office Cleaning'),
    (['deep clean', 'spring clean'], 'Deep Cleaning', "Builders' Clean"),
    (['end of tenancy', 'bond clean', 'vacate clean', 'end of lease'], 'End of Tenancy Cleaning', 'Body Corporate Cleaning'),
    (['moving out', 'move out', 'moving in', 'move in'], 'Move In / Move Out Cleaning', 'Office Cleaning'),
    (['carpet clean', 'carpet shampoo', 'stain'], 'Carpet Cleaning', 'Carpet & Hard Floor Care'),
    (['couch', 'sofa', 'upholstery'], 'Upholstery Cleaning', 'Carpet & Hard Floor Care'),
    (['window clean', 'windows cleaned', 'clean windows'], 'Window Cleaning', 'Commercial Window Cleaning'),
    (['oven clean'], 'Oven Cleaning', 'Office Cleaning'),
    (['water blast', 'waterblast', 'pressure wash', 'water blasting'], 'Water Blasting', 'Commercial Water Blasting'),
    (['house wash', 'soft wash', 'wash the house'], 'House Washing', 'Commercial Water Blasting'),
    (['gutter clean', 'clean gutters', 'clean the gutters'], 'Gutter Cleaning', 'Commercial Water Blasting'),
    (['moss', 'lichen', 'roof clean'], 'Roof Cleaning & Moss Treatment', 'Commercial Water Blasting'),
    (['builders clean', 'after builders', 'construction clean'], 'After-Builders Cleaning', "Builders' Clean"),
    (['mould', 'mold', 'mildew'], 'Mould Removal', 'Office Cleaning'),
    (['office clean', 'office cleaning'], 'Regular House Cleaning', 'Office Cleaning'),
    (['washroom', 'sanitary', 'hygiene'], 'Deep Cleaning', 'Washroom Hygiene Services'),
    (['locksmith', 'locked out', 'lock change', 'rekey', 'new locks'], 'Locksmith Services', None),
    (['builder', 'renovation', 'renovate'], 'Builders & Renovations', None),
    (['brick', 'bricklayer', 'masonry', 'block wall'], 'Bricklaying & Masonry', None),
    (['arborist', 'tree surgeon', 'tree trimming'], 'Arborist & Tree Services', None),
    (['gate', 'gates'], 'Gates', None),
    (['pest', 'pests', 'rats', 'mice', 'rodent', 'rodents', 'rats in the roof', 'mice in the', 'cockroach', 'wasps', 'fleas', 'borer'], 'Pest Control', None),
    (['chimney', 'flue', 'duct clean'], 'Chimney & Duct Cleaning', None),
    (['appliance repair', 'fridge repair', 'washing machine repair', 'oven repair', 'broken dishwasher'], 'Appliance Repairs', None),
    (['computer', 'laptop', 'printer', 'home it', 'tech support'], 'Home IT Support', None),
    (['inspection', 'inspector', 'pre-purchase', 'building report', 'builders report'], 'Building & Property Inspections', None),
    (['engineer', 'structural engineer', 'building services'], 'Building Service Engineering', None),
    (['architect', 'draughtsman', 'drafting', 'house plans'], 'Architecture & Drafting', None),
    (['rubbish', 'junk', 'skip bin', 'dump run'], 'Rubbish & Green Waste Removal', None),
    (['man with a van', 'local move', 'movers', 'furniture delivery'], 'Man with a Van / Local Movers', None),
    (['house move', 'removalist', 'removals', 'moving house'], 'Full-Service House Removals', None),
    (['elderly', 'caregiver', 'home help', 'independent living'], 'Elderly & Independent Living Support', None),
    (['pet', 'dog walking', 'dog grooming', 'pet sitting', 'cat sitting'], 'Pet Care & Grooming', None),
    (['tutor', 'tutoring', 'music lessons', 'piano lessons', 'homework'], 'In-Home Tutoring & Music Lessons', None),
    (['mortgage', 'insurance advice', 'insurance adviser'], 'Insurance & Mortgage Advisory', None),
    (['admin help', 'tech coaching', 'smartphone help', 'paperwork'], 'Personal Tech & Admin Coaching', None),
    (["hood clean", "kitchen exhaust", "canopy clean", "extraction hood"], None, "Commercial Kitchen & Hood Cleaning"),
]



def _detect_service(text: str, service_type: str = "residential") -> List[Dict[str, Any]]:
    import re
    taxonomy = COMMERCIAL_TAXONOMY if service_type == "commercial" else RESIDENTIAL_TAXONOMY
    t = " " + re.sub(r"[^a-z0-9\s-]", " ", text.lower()) + " "
    words = set(re.findall(r"[a-z]{4,}", t))
    by_name = {s["name"]: (c, s) for c in taxonomy for s in c["subcategories"]}
    scores: Dict[str, float] = {}
    for phrases, res_sub, com_sub in SERVICE_KEYWORDS:
        name = com_sub if service_type == "commercial" else res_sub
        if not name:
            continue
        if name not in by_name:
            continue
        for ph in phrases:
            if re.search(rf"\b{re.escape(ph)}\b", t):
                scores[name] = scores.get(name, 0) + (1 if res_sub == "Handyman Services" else 2 + len(ph.split()))
    for name in by_name:
        for w in re.findall(r"[a-z]{4,}", name.lower()):
            if w in words or w.rstrip("s") in words:
                scores[name] = scores.get(name, 0) + 1
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:3]
    out = []
    for name, sc in ranked:
        c, s = by_name[name]
        out.append({"category_id": c["id"], "category_name": c["name"], "category_icon": c["icon"], "category_color": c["color"],
                    "subcategory_id": s["id"], "subcategory_name": s["name"], "score": sc})
    return out


@api.get("/services/detect")
async def detect_service(text: str, service_type: str = "residential"):
    """Guess the job category/subcategory from a free-text job description."""
    matches = _detect_service(text[:1000], service_type)
    return {"match": matches[0] if matches else None, "alternatives": matches[1:]}


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



# ---------------- PAYMENTS (Stripe Checkout — cards, Google Pay, Apple Pay) ----------------
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
import certifi as _certifi
import stripe as _stripe_sdk
_stripe_sdk.ca_bundle_path = _certifi.where()  # Stripe's bundled CA list doesn't cover the payments proxy

PLATFORM_FEE_CLIENT = 0.05    # added to what the client pays
PLATFORM_FEE_PROVIDER = 0.05  # deducted from the provider's payout
STRIPE_PCT, STRIPE_FIXED = 0.027, 0.30  # NZ domestic card fee estimate, passed to the client


def _fee_breakdown(invoice_total: float) -> Dict[str, float]:
    base = round(float(invoice_total), 2)
    client_fee = round(base * PLATFORM_FEE_CLIENT, 2)
    # gross-up so the card fee on the final charge is covered by the client
    charge = round((base + client_fee + STRIPE_FIXED) / (1 - STRIPE_PCT), 2)
    card_fee = round(charge - base - client_fee, 2)
    provider_fee = round(base * PLATFORM_FEE_PROVIDER, 2)
    return {"invoice_total": base, "client_platform_fee": client_fee, "card_fee": card_fee, "total_charge": charge,
            "provider_platform_fee": provider_fee, "provider_payout": round(base - provider_fee, 2),
            "client_fee_rate": PLATFORM_FEE_CLIENT, "provider_fee_rate": PLATFORM_FEE_PROVIDER,
            "card_fee_note": f"Stripe card processing ({STRIPE_PCT * 100:.1f}% + ${STRIPE_FIXED:.2f})"}


async def _payable_invoice(job_id: str, user) -> Dict[str, Any]:
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    payer = job.get("approver_id") if job.get("billing_target") == "approver" and job.get("approver_id") else job["client_id"]
    if user["user_id"] not in (payer, job["client_id"]):
        raise HTTPException(status_code=403, detail="Only the client can pay this invoice")
    inv = await db.invoices.find_one({"job_id": job_id}, {"_id": 0})
    if not inv or not inv.get("total"):
        raise HTTPException(status_code=400, detail="The provider hasn't sent an invoice yet")
    return {"job": job, "invoice": inv}


def _stripe(request: Request) -> StripeCheckout:
    return StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY") or "sk_test_emergent",
                          webhook_url=f"{str(request.base_url)}api/webhook/stripe")


@api.get("/payments/invoice/{job_id}/quote")
async def payment_quote(job_id: str, user=Depends(require_user)):
    ctx = await _payable_invoice(job_id, user)
    paid = await db.payment_transactions.find_one({"job_id": job_id, "payment_status": "paid"}, {"_id": 0, "session_id": 1})
    return {**_fee_breakdown(ctx["invoice"]["total"]), "invoice_version": ctx["invoice"].get("version"), "paid": bool(paid)}


class PayInvoiceIn(BaseModel):
    origin_url: str


@api.post("/payments/invoice/{job_id}/checkout")
async def pay_invoice(job_id: str, payload: PayInvoiceIn, request: Request, user=Depends(require_user)):
    ctx = await _payable_invoice(job_id, user)
    if await db.payment_transactions.find_one({"job_id": job_id, "payment_status": "paid"}):
        raise HTTPException(status_code=400, detail="This invoice is already paid")
    origin = payload.origin_url.rstrip("/")
    if not origin.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid origin")
    fees = _fee_breakdown(ctx["invoice"]["total"])
    job = ctx["job"]
    req = CheckoutSessionRequest(
        amount=float(fees["total_charge"]), currency="nzd",
        success_url=f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/payment/cancel?job_id={job_id}",
        metadata={"job_id": job_id, "user_id": user["user_id"], "invoice_version": str(ctx["invoice"].get("version") or "")},
        payment_methods=["card"],  # Google Pay / Apple Pay appear automatically with cards when enabled in Stripe
    )
    session = await _stripe(request).create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "job_id": job_id, "user_id": user["user_id"],
        "provider_id": job.get("assigned_provider_id"), "amount": fees["total_charge"], "currency": "nzd",
        "fees": fees, "status": "initiated", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)})
    return {"checkout_url": session.url, "session_id": session.session_id}


async def _mark_paid(session_id: str):
    tx = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "payment_status": {"$ne": "paid"}},
        {"$set": {"status": "completed", "payment_status": "paid", "updated_at": datetime.now(timezone.utc)}})
    if not tx:
        return  # already processed
    job_id = tx["job_id"]
    now = datetime.now(timezone.utc)
    await db.jobs.update_one({"job_id": job_id}, {"$set": {"status": "done", "payment_status": "paid", "paid_at": now}})
    await db.invoices.update_one({"job_id": job_id}, {"$set": {"payment_status": "paid", "paid_at": now}})
    await db.bookings.update_many({"job_id": job_id}, {"$set": {"status": "paid", "price": tx["fees"]["invoice_total"],
                                                               "provider_payout": tx["fees"]["provider_payout"],
                                                               "platform_fee": tx["fees"]["provider_platform_fee"]}})
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0, "title": 1, "assigned_provider_id": 1})
    pid = (job or {}).get("assigned_provider_id") or tx.get("provider_id")
    if pid:
        await notify(pid, "job_paid", f"Invoice paid · payout ${tx['fees']['provider_payout']:.2f}",
                     f"{(job or {}).get('title', '')} (after 5% platform fee)", f"/jobs/{job_id}")


@api.get("/payments/status/{session_id}")
async def payment_status(session_id: str, request: Request):
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx["payment_status"] != "paid":
        try:
            st = await _stripe(request).get_checkout_status(session_id)
            if st.payment_status == "paid":
                await _mark_paid(session_id)
                tx["payment_status"], tx["status"] = "paid", "completed"
            elif st.status == "expired" and tx["status"] != "expired":
                await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"status": "expired", "payment_status": "expired"}})
                tx["payment_status"] = tx["status"] = "expired"
        except Exception as e:
            logging.warning(f"Stripe status check failed: {e}")
    return {"session_id": session_id, "status": tx["status"], "payment_status": tx["payment_status"], "job_id": tx["job_id"]}


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    try:
        ev = await _stripe(request).handle_webhook(body, request.headers.get("Stripe-Signature"))
    except Exception as e:
        logging.warning(f"Stripe webhook rejected: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")
    if ev.session_id and ev.payment_status == "paid":
        await _mark_paid(ev.session_id)
    return {"ok": True}


@api.get("/payments/history")
async def payment_history(user=Depends(require_user)):
    """Completed jobs with paid / unpaid state for clients and providers."""
    q = {"status": "done", "$or": [{"client_id": user["user_id"]}, {"assigned_provider_id": user["user_id"]}, {"approver_id": user["user_id"]}]}
    jobs = await db.jobs.find(q, {"_id": 0, "job_id": 1, "title": 1, "client_id": 1, "assigned_provider_id": 1, "payment_status": 1,
                                  "paid_at": 1, "created_at": 1, "location": 1}).sort("created_at", -1).to_list(300)
    invs = {i["job_id"]: i for i in await db.invoices.find({"job_id": {"$in": [j["job_id"] for j in jobs]}}, {"_id": 0, "job_id": 1, "total": 1}).to_list(None)}
    for j in jobs:
        j["invoice_total"] = (invs.get(j["job_id"]) or {}).get("total")
        j["payment_status"] = j.get("payment_status") or "unpaid"
        if j["invoice_total"]:
            j["fees"] = _fee_breakdown(j["invoice_total"])
    return jobs


# ---------------- RECEIPT SCANNER (Gemini vision) ----------------
RECEIPT_COST_TYPES = ("materials", "equipment_purchase", "equipment_hire", "third_party", "travel", "fuel", "other")
RECEIPT_MODEL = ("gemini", "gemini-3.8-flash")


class ReceiptScanIn(BaseModel):
    file_url: str


class ReceiptIn(BaseModel):
    file_url: Optional[str] = None
    cost_type: str
    supplier: Optional[str] = None
    date: Optional[str] = None
    total: float
    gst: Optional[float] = None
    items: List[Dict[str, Any]] = []
    notes: Optional[str] = None
    job_id: Optional[str] = None


async def _own_file(file_url: str, user) -> Dict[str, Any]:
    if not (file_url or "").startswith("/api/files/"):
        raise HTTPException(status_code=400, detail="Upload the receipt photo first")
    rec = await db.files.find_one({"file_id": file_url.split("/")[3], "is_deleted": False}, {"_id": 0})
    if not rec or rec.get("owner_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="File not found")
    return rec


@api.post("/receipts/scan")
async def scan_receipt(payload: ReceiptScanIn, user=Depends(require_user)):
    """AI reads supplier, date, totals and line items. The provider reviews before saving."""
    import asyncio, base64, json, re
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent, TextDelta, StreamDone
    await _require_provider(user)
    rec = await _own_file(payload.file_url, user)
    if not (rec.get("content_type") or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Scanning works with photos (JPG/PNG/WEBP) — enter PDF receipts manually")
    data, _ = await asyncio.to_thread(get_object, rec["storage_path"])
    chat = LlmChat(api_key=os.environ.get("EMERGENT_LLM_KEY", ""), session_id=f"receipt_{uuid.uuid4().hex[:8]}",
                   system_message="You extract data from New Zealand purchase receipts and reply with JSON only.").with_model(*RECEIPT_MODEL)
    prompt = ('Read this receipt. Reply ONLY with JSON: {"supplier": str|null, "date": "YYYY-MM-DD"|null, "total": number|null, '
              '"gst": number|null, "items": [{"description": str, "amount": number}], '
              '"suggested_cost_type": one of ["materials","equipment_purchase","equipment_hire","third_party","travel","fuel","other"], '
              '"is_receipt": bool}. Amounts in NZD as numbers. If it is not a receipt set is_receipt false.')
    text = ""
    try:
        async for ev in chat.stream_message(UserMessage(text=prompt, file_contents=[ImageContent(image_base64=base64.b64encode(data).decode())])):
            if isinstance(ev, TextDelta):
                text += ev.content
            elif isinstance(ev, StreamDone):
                break
    except Exception as e:
        logging.error(f"Receipt scan failed: {e}")
        raise HTTPException(status_code=502, detail="Couldn't read the receipt right now — enter the details manually")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        out = json.loads(m.group(0)) if m else {}
    except ValueError:
        out = {}
    if out.get("suggested_cost_type") not in RECEIPT_COST_TYPES:
        out["suggested_cost_type"] = "materials"
    out["items"] = [i for i in (out.get("items") or []) if isinstance(i, dict)][:30]
    return out


@api.post("/receipts")
async def save_receipt(payload: ReceiptIn, user=Depends(require_user)):
    await _require_provider(user)
    if payload.cost_type not in RECEIPT_COST_TYPES:
        raise HTTPException(status_code=400, detail="Choose a cost type")
    if not (0 < payload.total <= 1_000_000):
        raise HTTPException(status_code=400, detail="Total must be a positive amount")
    if payload.file_url:
        await _own_file(payload.file_url, user)
    job_title = None
    if payload.job_id:
        job = await db.jobs.find_one({"job_id": payload.job_id, "assigned_provider_id": user["user_id"]}, {"_id": 0, "title": 1})
        if not job:
            raise HTTPException(status_code=400, detail="You can only attach receipts to jobs assigned to you")
        job_title = job["title"]
    doc = {"receipt_id": f"rcpt_{uuid.uuid4().hex[:10]}", "provider_id": user["user_id"], "uploaded_by": user["user_id"],
           **payload.dict(), "job_title": job_title, "created_at": datetime.now(timezone.utc)}
    doc["items"] = doc["items"][:30]
    await db.receipts.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api.get("/receipts")
async def list_receipts(job_id: Optional[str] = None, user=Depends(require_user)):
    await _require_provider(user)
    q: Dict[str, Any] = {"provider_id": user["user_id"]}
    if job_id:
        q["job_id"] = job_id
    items = await db.receipts.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    totals: Dict[str, float] = {}
    for r in items:
        totals[r["cost_type"]] = round(totals.get(r["cost_type"], 0) + r["total"], 2)
    return {"receipts": items, "totals": totals, "grand_total": round(sum(totals.values()), 2)}


@api.delete("/receipts/{receipt_id}")
async def delete_receipt(receipt_id: str, user=Depends(require_user)):
    r = await db.receipts.delete_one({"receipt_id": receipt_id, "provider_id": user["user_id"]})
    if not r.deleted_count:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return {"ok": True}


# ---------------- ACTIVE JOB PROJECT TIMELINE ----------------
DEFAULT_STAGES = ["Job booked", "Site visit & scoping", "Materials ordered", "Work underway", "Final checks", "Completed"]


class TimelineUpdateIn(BaseModel):
    stage_index: Optional[int] = None
    message: Optional[str] = None
    photos: List[str] = []
    notify_client: bool = True


async def _timeline_job(job_id: str, user) -> tuple:
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    is_pro = user["user_id"] == job.get("assigned_provider_id")
    if not (is_pro or user["user_id"] in (job.get("client_id"), job.get("approver_id"))):
        raise HTTPException(status_code=403, detail="Not allowed")
    return job, is_pro


@api.get("/jobs/{job_id}/timeline")
async def get_timeline(job_id: str, user=Depends(require_user)):
    job, is_pro = await _timeline_job(job_id, user)
    updates = await db.job_updates.find({"job_id": job_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"stages": job.get("timeline_stages") or DEFAULT_STAGES, "current_stage": job.get("current_stage", 0),
            "updates": updates, "can_edit": is_pro and job.get("status") in ("assigned", "in_progress"), "status": job.get("status")}


@api.post("/jobs/{job_id}/timeline")
async def post_timeline_update(job_id: str, payload: TimelineUpdateIn, user=Depends(require_user)):
    job, is_pro = await _timeline_job(job_id, user)
    if not is_pro:
        raise HTTPException(status_code=403, detail="Only the assigned provider can post project updates")
    if job.get("status") not in ("assigned", "in_progress"):
        raise HTTPException(status_code=400, detail="Updates can only be posted on active jobs")
    stages = job.get("timeline_stages") or DEFAULT_STAGES
    msg = (payload.message or "").strip()[:2000]
    photos = [p for p in payload.photos if isinstance(p, str) and p.startswith("/api/files/")][:10]
    upd: Dict[str, Any] = {}
    stage = job.get("current_stage", 0)
    if payload.stage_index is not None:
        if not (0 <= payload.stage_index < len(stages)):
            raise HTTPException(status_code=400, detail="Unknown stage")
        stage = payload.stage_index
        upd["current_stage"] = stage
        if job.get("status") == "assigned" and stage > 0:
            upd["status"] = "in_progress"
    if not msg and not photos and "current_stage" not in upd:
        raise HTTPException(status_code=400, detail="Add a message, photo or stage change")
    if upd:
        await db.jobs.update_one({"job_id": job_id}, {"$set": upd})
    doc = {"update_id": f"upd_{uuid.uuid4().hex[:10]}", "job_id": job_id, "author_id": user["user_id"], "author_name": user.get("name"),
           "stage_index": stage, "stage": stages[stage], "stage_changed": "current_stage" in upd, "message": msg or None,
           "photos": photos, "sent_to_client": payload.notify_client, "created_at": datetime.now(timezone.utc)}
    await db.job_updates.insert_one(dict(doc))
    if payload.notify_client:
        target = job.get("approver_id") if job.get("billing_target") == "approver" and job.get("approver_id") else job["client_id"]
        await notify(target, "job_update", f"Update on {job.get('title')}: {stages[stage]}", msg[:120], f"/jobs/{job_id}")
    return doc


# ---------------- PROVIDER SPECIALIZATIONS + MATCHING ENGINE ----------------
PRICING_TYPES = ("small_fixed", "hourly", "large_quote")
BUSINESS_SIZES = ("solo", "small_team", "medium_enterprise")
AVAILABILITY = ("available", "busy")
SERVICE_TRACKS = ("residential", "commercial")
OPEN_JOB_STATUSES = ("open", "matched")


def _tax_index(service_type: str) -> Dict[str, Dict[str, Any]]:
    return COMMERCIAL_TAXONOMY_INDEX if service_type == "commercial" else RESIDENTIAL_TAXONOMY_INDEX


async def notify(user_id: str, kind: str, title: str, body: str = "", link: Optional[str] = None):
    await db.notifications.insert_one({
        "notification_id": f"ntf_{uuid.uuid4().hex[:10]}", "user_id": user_id, "type": kind,
        "title": title, "body": body, "link": link, "read": False,
        "created_at": datetime.now(timezone.utc),
    })


def _area_ok(profile: Dict[str, Any], job: Dict[str, Any]) -> bool:
    """Service-area check: listed suburbs must appear in the job location; otherwise fall back to radius."""
    suburbs = [x.strip().lower() for x in (profile.get("service_area_suburbs") or []) if x and x.strip()]
    loc = f"{job.get('location_suburb') or ''} {job.get('location') or ''}".lower()
    if suburbs:
        return any(sb in loc for sb in suburbs)
    radius = profile.get("service_radius_km")
    if radius and profile.get("latitude") is not None and job.get("location_lat") is not None:
        return _haversine_km(profile["latitude"], profile["longitude"], job["location_lat"], job["location_lng"]) <= radius
    return True


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def dispatch_job(job: Dict[str, Any]) -> int:
    """Strict specialization filter → one JobMatch per qualifying provider + dashboard alert. Idempotent."""
    q: Dict[str, Any] = {"service_type": job.get("service_type", "residential"), "category_id": job["category"],
                         "pricing_modes": job.get("pricing_type", "large_quote")}
    if job.get("subcategory"):
        q["subcategory_id"] = job["subcategory"]
    specs = await db.provider_specializations.find(q, {"_id": 0, "provider_id": 1}).to_list(None)
    provider_ids = list({sp["provider_id"] for sp in specs} - {job.get("client_id"), job.get("approver_id")})
    if not provider_ids:
        return 0
    profiles = await db.provider_profiles.find({"user_id": {"$in": provider_ids}}, {"_id": 0}).to_list(None)
    existing = {m["provider_id"] for m in await db.job_matches.find({"job_id": job["job_id"]}, {"provider_id": 1, "_id": 0}).to_list(None)}
    created = 0
    for prof in profiles:
        tracks = prof.get("service_tracks") or list(SERVICE_TRACKS)
        if job.get("service_type", "residential") not in tracks or not _area_ok(prof, job):
            continue
        if prof["user_id"] in existing:
            continue
        await db.job_matches.insert_one({
            "match_id": f"mt_{uuid.uuid4().hex[:10]}", "job_id": job["job_id"], "provider_id": prof["user_id"],
            "provider_name": prof.get("business_name", ""), "match_status": "notified",
            "quote_amount": None, "message": None, "available_from": None,
            "created_at": datetime.now(timezone.utc), "responded_at": None,
        })
        await notify(prof["user_id"], "job_match", "New matched job",
                     f"{job.get('title')} · {job.get('location') or ''}".strip(" ·"), "/provider/dashboard")
        created += 1
    total = len(existing) + created
    upd: Dict[str, Any] = {"matched_count": total}
    if total and job.get("status") == "open":
        upd["status"] = "matched"
    await db.jobs.update_one({"job_id": job["job_id"]}, {"$set": upd})
    return total


class SpecializationIn(BaseModel):
    service_type: str
    category_id: str
    subcategory_id: str
    pricing_modes: List[str]
    rate: Optional[float] = None


class OnboardingIn(BaseModel):
    business_name: str
    business_size: str
    service_area_suburbs: List[str] = []
    service_tracks: List[str]
    bio: Optional[str] = None
    specializations: List[SpecializationIn]


def _validated_specs(items: List[SpecializationIn], tracks: List[str], provider_id: str) -> List[Dict[str, Any]]:
    if not items:
        raise HTTPException(status_code=400, detail="Select at least one category and subcategory")
    out, seen = [], set()
    for it in items:
        if it.service_type not in SERVICE_TRACKS:
            raise HTTPException(status_code=400, detail="service_type must be residential or commercial")
        if it.service_type not in tracks:
            raise HTTPException(status_code=400, detail=f"You don't serve {it.service_type} clients — update your service tracks")
        meta = _tax_index(it.service_type).get(f"{it.category_id}/{it.subcategory_id}")
        if not meta:
            raise HTTPException(status_code=400, detail=f"Unknown {it.service_type} service {it.category_id}/{it.subcategory_id}")
        modes = [m for m in dict.fromkeys(it.pricing_modes) if m in PRICING_TYPES]
        if not modes:
            raise HTTPException(status_code=400, detail=f"Choose at least one job size for {meta['sub_name']}")
        if it.rate is not None and not (0 < it.rate <= 100000):
            raise HTTPException(status_code=400, detail="Rate must be a positive number")
        key = (it.service_type, it.category_id, it.subcategory_id)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "spec_id": f"spec_{uuid.uuid4().hex[:10]}", "provider_id": provider_id, "service_type": it.service_type,
            "category_id": it.category_id, "category_name": meta["category_name"],
            "subcategory_id": it.subcategory_id, "subcategory_name": meta["sub_name"],
            "pricing_modes": modes, "rate": it.rate, "created_at": datetime.now(timezone.utc),
        })
    return out


async def _require_provider(user) -> None:
    if user.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only service providers can do this")


@api.get("/providers/me/onboarding")
async def get_onboarding(user=Depends(require_user)):
    await _require_provider(user)
    prof = await db.provider_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    specs = await db.provider_specializations.find({"provider_id": user["user_id"]}, {"_id": 0}).to_list(None)
    return {"profile": prof, "specializations": specs, "onboarded": bool(prof.get("onboarded")) and len(specs) > 0}


@api.put("/providers/me/onboarding")
async def save_onboarding(payload: OnboardingIn, user=Depends(require_user)):
    await _require_provider(user)
    if not payload.business_name.strip():
        raise HTTPException(status_code=400, detail="Business name is required")
    if payload.business_size not in BUSINESS_SIZES:
        raise HTTPException(status_code=400, detail="business_size must be solo, small_team or medium_enterprise")
    tracks = [t for t in dict.fromkeys(payload.service_tracks) if t in SERVICE_TRACKS]
    if not tracks:
        raise HTTPException(status_code=400, detail="Choose Residential, Commercial or both")
    specs = _validated_specs(payload.specializations, tracks, user["user_id"])
    suburbs = [x.strip() for x in payload.service_area_suburbs if x and x.strip()][:50]
    cats = sorted({sp["category_id"] for sp in specs})
    await db.provider_profiles.update_one({"user_id": user["user_id"]}, {"$set": {
        "business_name": payload.business_name.strip(), "business_size": payload.business_size,
        "service_area_suburbs": suburbs, "service_tracks": tracks, "categories": cats,
        **({"bio": payload.bio.strip()} if payload.bio is not None else {}),
        "onboarded": True,
    }, "$setOnInsert": {"rating": 0.0, "reviews_count": 0, "jobs_completed": 0, "verified": False,
                        "availability_status": "available"}}, upsert=True)
    await db.provider_specializations.delete_many({"provider_id": user["user_id"]})
    await db.provider_specializations.insert_many([dict(sp) for sp in specs])
    # Pick up any open jobs that now match
    open_jobs = await db.jobs.find({"status": {"$in": list(OPEN_JOB_STATUSES)}, "approval_status": {"$ne": "pending"},
                                    "category": {"$in": cats}}, {"_id": 0}).to_list(500)
    for j in open_jobs:
        await dispatch_job(j)
    return await get_onboarding(user)


@api.get("/providers/{provider_id}/specializations")
async def provider_specializations(provider_id: str, user=Depends(require_user)):
    return await db.provider_specializations.find({"provider_id": provider_id}, {"_id": 0, "provider_id": 0}).sort("category_name", 1).to_list(None)


# ---- Matches (DispatchQueue) ----
def _strip_private(job: Dict[str, Any], awarded: bool) -> Dict[str, Any]:
    return job if awarded else {k: v for k, v in job.items() if k != "access_notes"}


@api.get("/matches/mine")
async def my_matches(user=Depends(require_user)):
    await _require_provider(user)
    matches = await db.job_matches.find({"provider_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    jobs = await db.jobs.find({"job_id": {"$in": [m["job_id"] for m in matches]}}, {"_id": 0}).to_list(None)
    for j in jobs:
        meta = _tax_index(j.get("service_type", "residential")).get(f"{j.get('category')}/{j.get('subcategory')}")
        if meta:
            j["category_name"], j["subcategory_name"] = meta["category_name"], meta["sub_name"]
    jm = {j["job_id"]: j for j in jobs}
    out = []
    for m in matches:
        j = jm.get(m["job_id"])
        if j:
            m["job"] = _strip_private(j, m["match_status"] == "awarded")
            out.append(m)
    return out


async def _own_match(match_id: str, user) -> tuple:
    await _require_provider(user)
    m = await db.job_matches.find_one({"match_id": match_id}, {"_id": 0})
    if not m or m["provider_id"] != user["user_id"]:
        raise HTTPException(status_code=404, detail="Match not found")
    job = await db.jobs.find_one({"job_id": m["job_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return m, job


class MatchAcceptIn(BaseModel):
    message: Optional[str] = None
    available_from: Optional[str] = None


class MatchQuoteIn(BaseModel):
    amount: float
    message: Optional[str] = None


async def _respond(m, job, update: Dict[str, Any], note: str):
    if job["status"] not in OPEN_JOB_STATUSES or m["match_status"] in ("closed", "awarded", "declined"):
        raise HTTPException(status_code=400, detail="This job is no longer open")
    update["responded_at"] = datetime.now(timezone.utc)
    await db.job_matches.update_one({"match_id": m["match_id"]}, {"$set": update})
    await notify(job.get("billing_target") == "approver" and job.get("approver_id") or job["client_id"],
                 "match_response", note, job.get("title", ""), f"/jobs/{job['job_id']}")
    return await db.job_matches.find_one({"match_id": m["match_id"]}, {"_id": 0})


@api.post("/matches/{match_id}/accept")
async def accept_match(match_id: str, payload: MatchAcceptIn, user=Depends(require_user)):
    m, job = await _own_match(match_id, user)
    if job.get("pricing_type") == "large_quote":
        raise HTTPException(status_code=400, detail="Large projects need a fixed quote — use Submit quote")
    return await _respond(m, job, {"match_status": "accepted", "message": (payload.message or "").strip()[:1000] or None,
                                   "available_from": payload.available_from},
                          f"{m.get('provider_name') or 'A pro'} accepted your job")


@api.post("/matches/{match_id}/quote")
async def quote_match(match_id: str, payload: MatchQuoteIn, user=Depends(require_user)):
    m, job = await _own_match(match_id, user)
    if not (0 < payload.amount <= 10_000_000):
        raise HTTPException(status_code=400, detail="Quote must be a positive amount")
    return await _respond(m, job, {"match_status": "quote_submitted", "quote_amount": round(payload.amount, 2),
                                   "message": (payload.message or "").strip()[:2000] or None},
                          f"New quote from {m.get('provider_name') or 'a pro'}: ${payload.amount:,.0f}")


@api.post("/matches/{match_id}/decline")
async def decline_match(match_id: str, user=Depends(require_user)):
    m, job = await _own_match(match_id, user)
    if m["match_status"] in ("awarded",):
        raise HTTPException(status_code=400, detail="You've already been awarded this job")
    await db.job_matches.update_one({"match_id": match_id}, {"$set": {"match_status": "declined", "responded_at": datetime.now(timezone.utc)}})
    return {"ok": True}


async def _client_job(job_id: str, user) -> Dict[str, Any]:
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if user["user_id"] not in (job.get("client_id"), job.get("approver_id")):
        raise HTTPException(status_code=403, detail="Not allowed")
    return job


@api.get("/jobs/{job_id}/matches")
async def job_matches(job_id: str, user=Depends(require_user)):
    await _client_job(job_id, user)
    matches = await db.job_matches.find({"job_id": job_id}, {"_id": 0}).sort("created_at", 1).to_list(None)
    profs = await db.provider_profiles.find({"user_id": {"$in": [m["provider_id"] for m in matches]}},
                                            {"_id": 0, "user_id": 1, "business_name": 1, "rating": 1, "reviews_count": 1,
                                             "verified": 1, "qualified_verified": 1, "police_checked": 1, "business_size": 1, "availability_status": 1, "hourly_rate": 1}).to_list(None)
    pm = {p["user_id"]: p for p in profs}
    for m in matches:
        m["provider"] = pm.get(m["provider_id"], {})
    responded = [m for m in matches if m["match_status"] in ("accepted", "quote_submitted", "awarded")]
    return {"notified": len(matches), "responded": len(responded), "matches": matches}


class AwardIn(BaseModel):
    match_id: str


@api.post("/jobs/{job_id}/award")
async def award_job(job_id: str, payload: AwardIn, user=Depends(require_user)):
    job = await _client_job(job_id, user)
    if job["status"] not in OPEN_JOB_STATUSES:
        raise HTTPException(status_code=400, detail="This job has already been awarded")
    m = await db.job_matches.find_one({"match_id": payload.match_id, "job_id": job_id}, {"_id": 0})
    if not m or m["match_status"] not in ("accepted", "quote_submitted"):
        raise HTTPException(status_code=400, detail="You can only award a pro who accepted or quoted")
    prof = await db.provider_profiles.find_one({"user_id": m["provider_id"]}, {"_id": 0}) or {}
    pt = job.get("pricing_type")
    if m.get("quote_amount"):
        amount = m["quote_amount"]
    elif pt == "hourly":
        amount = round((job.get("budget_or_estimate") or 1) * (prof.get("hourly_rate") or 85.0), 2)
    else:
        amount = job.get("budget_or_estimate") or job.get("budget_max") or 0
    now = datetime.now(timezone.utc)
    await db.job_matches.update_one({"match_id": m["match_id"]}, {"$set": {"match_status": "awarded"}})
    await db.job_matches.update_many({"job_id": job_id, "match_id": {"$ne": m["match_id"]}}, {"$set": {"match_status": "closed"}})
    await db.jobs.update_one({"job_id": job_id}, {"$set": {"status": "assigned", "assigned_provider_id": m["provider_id"], "awarded_at": now}})
    # Keep invoices / timesheets / access-notes working: record the win as an accepted bid + booking
    pro_user = await db.users.find_one({"user_id": m["provider_id"]}, {"_id": 0, "name": 1})
    bid = {"bid_id": f"bid_{uuid.uuid4().hex[:10]}", "job_id": job_id, "provider_id": m["provider_id"],
           "provider_name": prof.get("business_name") or (pro_user or {}).get("name", ""), "amount": amount,
           "message": m.get("message") or "", "eta_days": 2, "status": "accepted", "created_at": now, "source": "match"}
    await db.bids.insert_one(dict(bid))
    sched = now + timedelta(days=2)
    if job.get("preferred_date"):
        try:
            sched = datetime.strptime(job["preferred_date"][:10], "%Y-%m-%d").replace(hour=9, tzinfo=timezone.utc)
        except ValueError:
            pass
    client_user = await db.users.find_one({"user_id": job["client_id"]}, {"_id": 0, "name": 1}) or {}
    booking = Booking(client_id=job["client_id"], client_name=client_user.get("name") or user["name"], provider_id=m["provider_id"],
                      provider_name=bid["provider_name"], job_id=job_id, category=job["category"], price=amount,
                      scheduled_at=sched, address=job.get("location", "Auckland"))
    await db.bookings.insert_one(booking.dict())
    await notify(m["provider_id"], "job_awarded", "You won a job!", job.get("title", ""), "/provider/dashboard")
    others = await db.job_matches.find({"job_id": job_id, "match_status": "closed"}, {"provider_id": 1, "_id": 0}).to_list(None)
    for o in others:
        await notify(o["provider_id"], "job_closed", "Job filled by another pro", job.get("title", ""), "/provider/dashboard")
    return {"ok": True, "job_id": job_id, "assigned_provider_id": m["provider_id"], "amount": amount}


class JobProgressIn(BaseModel):
    status: str  # in_progress | done


@api.post("/jobs/{job_id}/progress")
async def job_progress(job_id: str, payload: JobProgressIn, user=Depends(require_user)):
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if user["user_id"] not in (job.get("assigned_provider_id"), job.get("client_id")):
        raise HTTPException(status_code=403, detail="Not allowed")
    allowed = {"assigned": ["in_progress", "done"], "in_progress": ["done"]}
    if payload.status not in allowed.get(job["status"], []):
        raise HTTPException(status_code=400, detail=f"Can't move a {job['status']} job to {payload.status}")
    await db.jobs.update_one({"job_id": job_id}, {"$set": {"status": payload.status}})
    # keep the booking in sync so provider stats / earnings reflect match jobs
    await db.bookings.update_many({"job_id": job_id, "provider_id": job.get("assigned_provider_id"), "status": {"$nin": ["paid", "cancelled"]}},
                                  {"$set": {"status": "done" if payload.status == "done" else "working"}})
    other = job["client_id"] if user["user_id"] == job.get("assigned_provider_id") else job.get("assigned_provider_id")
    if other:
        await notify(other, "job_status", "Job started" if payload.status == "in_progress" else "Job completed",
                     job.get("title", ""), f"/jobs/{job_id}")
    return {"ok": True, "status": payload.status}


# ---- Notifications ----
@api.get("/notifications/mine")
async def my_notifications(user=Depends(require_user)):
    items = await db.notifications.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    unread = await db.notifications.count_documents({"user_id": user["user_id"], "read": False})
    return {"unread": unread, "items": items}


@api.post("/notifications/read-all")
async def read_all_notifications(user=Depends(require_user)):
    await db.notifications.update_many({"user_id": user["user_id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}


# ---- Seed: sample specializations so the matching engine works out of the box ----
SEED_SPECS = {
    "Demo Trade Co.": {"tracks": ["residential", "commercial"], "size": "small_team", "suburbs": [], "specs": [
        ("residential", "general-home-maintenance", "Handyman Services", ["small_fixed", "hourly", "large_quote"], 85),
        ("residential", "plumbing-gas", "Tap & Toilet Repairs", ["small_fixed", "hourly"], 95),
        ("residential", "plumbing-gas", "Leak Repairs", ["small_fixed", "hourly", "large_quote"], 95),
        ("commercial", "building-maintenance", "Commercial Handyman", ["hourly", "large_quote"], 110)]},
    "Sarah Chen Plumbing": {"tracks": ["residential", "commercial"], "size": "solo",
                            "suburbs": ["Auckland Central", "Ponsonby", "Grey Lynn", "Mount Eden", "Parnell"], "specs": [
        ("residential", "plumbing-gas", "Tap & Toilet Repairs", ["small_fixed", "hourly"], 95),
        ("residential", "plumbing-gas", "Hot Water Systems", ["hourly", "large_quote"], 95),
        ("residential", "plumbing-gas", "Blocked Drains", ["small_fixed", "hourly"], 95),
        ("commercial", "plumbing-gas", "Commercial Plumbing", ["hourly", "large_quote"], 120)]},
    "MP Electrical": {"tracks": ["residential", "commercial"], "size": "medium_enterprise", "suburbs": [], "specs": [
        ("residential", "electrical", "Power Points & Switches", ["small_fixed", "hourly"], 105),
        ("residential", "electrical", "Switchboard Upgrades", ["large_quote"], 105),
        ("commercial", "electrical", "LED Retrofits", ["large_quote"], 125),
        ("commercial", "electrical", "Switchboard Upgrades", ["large_quote"], 125)]},
    "SparkClean Services": {"tracks": ["residential", "commercial"], "size": "small_team", "suburbs": [], "specs": [
        ("residential", "cleaning", "Regular House Cleaning", ["small_fixed", "hourly"], 55),
        ("residential", "cleaning", "End of Tenancy Cleaning", ["small_fixed", "large_quote"], 55),
        ("commercial", "commercial-cleaning", "Office Cleaning", ["hourly", "large_quote"], 65),
        ("commercial", "commercial-cleaning", "Commercial Kitchen & Hood Cleaning", ["large_quote"], 80)]},
}


async def seed_specializations():
    for biz, cfg in SEED_SPECS.items():
        prof = await db.provider_profiles.find_one({"business_name": biz}, {"_id": 0, "user_id": 1})
        if not prof or await db.provider_specializations.count_documents({"provider_id": prof["user_id"]}):
            continue
        docs = []
        for st, cat, sub_name, modes, rate in cfg["specs"]:
            meta = _tax_index(st).get(f"{cat}/{_slug(sub_name)}")
            if not meta:
                logging.warning(f"Seed spec not in taxonomy: {st} {cat}/{sub_name}")
                continue
            docs.append({"spec_id": f"spec_{uuid.uuid4().hex[:10]}", "provider_id": prof["user_id"], "service_type": st,
                         "category_id": cat, "category_name": meta["category_name"], "subcategory_id": meta["sub_id"],
                         "subcategory_name": meta["sub_name"], "pricing_modes": modes, "rate": rate,
                         "created_at": datetime.now(timezone.utc)})
        if docs:
            await db.provider_specializations.insert_many(docs)
        await db.provider_profiles.update_one({"user_id": prof["user_id"]}, {"$set": {
            "service_tracks": cfg["tracks"], "business_size": cfg["size"], "service_area_suburbs": cfg["suburbs"],
            "onboarded": True, "categories": sorted({d["category_id"] for d in docs})}})
        await db.provider_profiles.update_one({"user_id": prof["user_id"], "availability_status": {"$exists": False}},
                                              {"$set": {"availability_status": "available"}})


@app.on_event("startup")
async def on_startup():
    try:
        init_storage()
    except Exception as e:
        logging.getLogger(__name__).error(f"Storage init failed: {e}")
    await seed_data()
    await seed_demo_accounts()
    await seed_specializations()
    await db.job_matches.create_index([("provider_id", 1), ("created_at", -1)])
    await db.job_matches.create_index([("job_id", 1), ("provider_id", 1)], unique=True)
    await db.provider_specializations.create_index([("service_type", 1), ("category_id", 1), ("subcategory_id", 1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
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
