"""
Dispatchr Backend - Home Services Marketplace
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

app = FastAPI(title="Dispatchr API")
api = APIRouter(prefix="/api")


# ---------------- MODELS ----------------
class UserBase(BaseModel):
    email: str
    name: str
    role: str = "customer"  # customer, provider, property, insurance
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
    location: str = "Auckland"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    urgency: str = "flexible"  # asap, this_week, within_month, flexible
    mode: str = "quotes"  # quotes, instant
    status: str = "open"  # open, in_progress, done, cancelled
    photos: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobCreate(BaseModel):
    title: str
    description: str
    category: str
    location: str = "Auckland"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    urgency: str = "flexible"
    mode: str = "quotes"
    photos: List[str] = []


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
    authorization: Optional[str] = Header(default=None),
) -> Optional[Dict[str, Any]]:
    """Try Google OAuth session_token first, then JWT bearer."""
    token = None
    is_session = False
    if session_token:
        token = session_token
        is_session = True
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        # Could be either JWT or session token
    if not token:
        return None

    # Try session token in DB first
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        expires_at = session.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at < datetime.now(timezone.utc):
            return None
        user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})
        return user

    # Try JWT
    if not is_session:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            user_id = payload.get("user_id")
            if user_id:
                user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
                return user
        except Exception:
            pass
    return None


async def require_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ---------------- AUTH ROUTES ----------------
@api.post("/auth/register")
async def register(payload: UserCreate):
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
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    return {"user": doc, "token": token}


@api.post("/auth/login")
async def login(payload: UserLogin, response: Response):
    user = await db.users.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(user["user_id"])
    user.pop("_id", None)
    user.pop("password_hash", None)
    return {"user": user, "token": token}


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
    return {"ok": True}


@api.patch("/auth/role")
async def switch_role(request: Request, user=Depends(require_user)):
    body = await request.json()
    role = body.get("role")
    if role not in ["customer", "provider", "property", "insurance"]:
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
    job = JobPost(client_id=user["user_id"], **payload.dict())
    await db.jobs.insert_one(job.dict())
    return job


@api.get("/jobs/mine")
async def my_jobs(user=Depends(require_user)):
    jobs = await db.jobs.find({"client_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    if not jobs:
        return jobs
    # Batch fetch all bids for these jobs (avoids N+1)
    job_ids = [j["job_id"] for j in jobs]
    all_bids = await db.bids.find({"job_id": {"$in": job_ids}}, {"_id": 0}).to_list(None)
    bids_by_job = {}
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
    q: Dict[str, Any] = {"status": "open"}
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
    return {"message": "Dispatchr API", "version": "1.0"}


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
                "hourly_rate": p["rate"],
                "rating": p["rating"],
                "reviews_count": p["reviews"],
                "jobs_completed": p["jobs"],
                "verified": True,
                "insured": True,
                "plan": "pro",
                "latitude": p["lat"],
                "longitude": p["lng"],
                "online": True,
                "bio": f"Trusted {p['cats'][0]} professionals in Auckland.",
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


@app.on_event("startup")
async def on_startup():
    await seed_data()
    logging.info("Dispatchr startup complete")


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
