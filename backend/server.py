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
JWT_SECRET = os.environ.get("JWT_SECRET", "dispatchr-secret-key-change-me")
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
    amount: float
    message: str
    eta_days: int = 3
    status: str = "pending"  # pending, accepted, rejected
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BidCreate(BaseModel):
    job_id: str
    amount: float
    message: str
    eta_days: int = 3


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
    # Attach bids count
    for j in jobs:
        bids = await db.bids.find({"job_id": j["job_id"]}, {"_id": 0}).to_list(200)
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
        amount=payload.amount,
        message=payload.message,
        eta_days=payload.eta_days,
    )
    await db.bids.insert_one(bid.dict())
    return bid


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
    for b in bids:
        job = await db.jobs.find_one({"job_id": b["job_id"]}, {"_id": 0})
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
    for p in profiles:
        u = await db.users.find_one({"user_id": p["user_id"]}, {"_id": 0, "password_hash": 0})
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
    # PRODUCTS
    if await db.products.count_documents({}) == 0:
        products = [
            # Heat Pumps
            {"product_id": "p001", "name": "Mitsubishi 5kW Inverter Heat Pump", "category": "Heating & Cooling", "price": 2499.0, "original_price": 2899.0, "discount": 14, "image": "https://images.unsplash.com/photo-1631545308456-c1eb1c1d0c0f?w=500&auto=format", "brand": "Mitsubishi", "description": "Energy efficient inverter heat pump, ideal for medium rooms.", "in_stock": True, "rating": 4.7, "reviews_count": 128},
            {"product_id": "p002", "name": "Daikin 7kW Premium Heat Pump", "category": "Heating & Cooling", "price": 3299.0, "original_price": 3799.0, "discount": 13, "image": "https://images.unsplash.com/photo-1585129777188-95d16bec91b9?w=500&auto=format", "brand": "Daikin", "description": "Whisper quiet, ideal for large open plan living.", "in_stock": True, "rating": 4.8, "reviews_count": 92},
            {"product_id": "p003", "name": "Fujitsu 3.2kW Hi-Wall Heat Pump", "category": "Heating & Cooling", "price": 1999.0, "original_price": 2499.0, "discount": 20, "image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=500&auto=format", "brand": "Fujitsu", "description": "Compact and reliable for bedrooms.", "in_stock": True, "rating": 4.5, "reviews_count": 61},
            # Solar
            {"product_id": "p004", "name": "SolarMax 6.6kW Solar Panel Kit", "category": "Lighting & Electrical", "price": 5999.0, "original_price": 7499.0, "discount": 20, "image": "https://images.unsplash.com/photo-1509391366360-2e959784a276?w=500&auto=format", "brand": "SolarMax", "description": "Complete grid-tie kit with inverter and mounting.", "in_stock": True, "rating": 4.6, "reviews_count": 44},
            # Appliances
            {"product_id": "p005", "name": "Fisher & Paykel 8.5kg Front Loader", "category": "Appliances & Laundry", "price": 1299.0, "original_price": 1599.0, "discount": 19, "image": "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?w=500&auto=format", "brand": "Fisher & Paykel", "description": "Energy efficient washer with steam refresh.", "in_stock": True, "rating": 4.7, "reviews_count": 210},
            {"product_id": "p006", "name": "Bosch 60cm Dishwasher", "category": "Appliances & Laundry", "price": 999.0, "original_price": 1299.0, "discount": 23, "image": "https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?w=500&auto=format", "brand": "Bosch", "description": "Quiet operation, 5 wash programs.", "in_stock": True, "rating": 4.6, "reviews_count": 87},
            # Kitsets
            {"product_id": "p007", "name": "GardenMaster 3x3m Steel Shed Kit", "category": "Home & Garden", "price": 1899.0, "original_price": 2299.0, "discount": 17, "image": "https://images.unsplash.com/photo-1602103928956-a19dc37d1e30?w=500&auto=format", "brand": "GardenMaster", "description": "Full DIY steel shed kit with concrete anchors.", "in_stock": True, "rating": 4.4, "reviews_count": 35},
            # Hot water
            {"product_id": "p008", "name": "Rheem 250L Hot Water Cylinder", "category": "Plumbing", "price": 1899.0, "original_price": 2199.0, "discount": 14, "image": "https://images.unsplash.com/photo-1620626011761-996317b8d101?w=500&auto=format", "brand": "Rheem", "description": "Mains pressure electric cylinder.", "in_stock": True, "rating": 4.5, "reviews_count": 74},
            # Bathroom
            {"product_id": "p009", "name": "Complete Bathroom Renovation Kit", "category": "Bathroom", "price": 4999.0, "original_price": 5999.0, "discount": 17, "image": "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=500&auto=format", "brand": "Bathroom Co", "description": "Vanity, toilet, shower and taps in one package.", "in_stock": True, "rating": 4.6, "reviews_count": 22},
            {"product_id": "p010", "name": "Modern Vanity 900mm", "category": "Bathroom", "price": 799.0, "original_price": 999.0, "discount": 20, "image": "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=500&auto=format", "brand": "Ceramica", "description": "Wall hung vanity with stone top.", "in_stock": True, "rating": 4.5, "reviews_count": 41},
            # Kitchen
            {"product_id": "p011", "name": "Kitchen Tap Mixer Chrome", "category": "Kitchen", "price": 249.0, "original_price": 349.0, "discount": 29, "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=500&auto=format", "brand": "Methven", "description": "Pull-out spray kitchen mixer.", "in_stock": True, "rating": 4.7, "reviews_count": 156},
            {"product_id": "p012", "name": "Stainless Steel Undermount Sink", "category": "Kitchen", "price": 399.0, "original_price": 499.0, "discount": 20, "image": "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=500&auto=format", "brand": "Blanco", "description": "Double bowl undermount sink.", "in_stock": True, "rating": 4.6, "reviews_count": 63},
            # Lighting
            {"product_id": "p013", "name": "LED Downlight Pack of 10", "category": "Lighting & Electrical", "price": 149.0, "original_price": 199.0, "discount": 25, "image": "https://images.unsplash.com/photo-1524661135-423995f22d0b?w=500&auto=format", "brand": "Philips", "description": "9W dimmable LED downlights, cool white.", "in_stock": True, "rating": 4.8, "reviews_count": 342},
            {"product_id": "p014", "name": "Smart Doorbell with Camera", "category": "Smart Home", "price": 299.0, "original_price": 399.0, "discount": 25, "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=500&auto=format", "brand": "Ring", "description": "1080p video doorbell with two-way audio.", "in_stock": True, "rating": 4.5, "reviews_count": 189},
            # Tools & Hardware
            {"product_id": "p015", "name": "Makita 18V Cordless Drill Kit", "category": "Tools & Hardware", "price": 499.0, "original_price": 649.0, "discount": 23, "image": "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=500&auto=format", "brand": "Makita", "description": "Combi drill + impact driver with 2 batteries.", "in_stock": True, "trade_only": True, "rating": 4.9, "reviews_count": 512},
            {"product_id": "p016", "name": "DeWalt Circular Saw 184mm", "category": "Tools & Hardware", "price": 399.0, "original_price": 499.0, "discount": 20, "image": "https://images.unsplash.com/photo-1581092160562-40aa08e78837?w=500&auto=format", "brand": "DeWalt", "description": "1600W circular saw with laser guide.", "in_stock": True, "trade_only": True, "rating": 4.7, "reviews_count": 88},
            # Paint
            {"product_id": "p017", "name": "Dulux Wash&Wear 10L White", "category": "Paint & Decorating", "price": 189.0, "original_price": 229.0, "discount": 17, "image": "https://images.unsplash.com/photo-1562259949-e8e7689d7828?w=500&auto=format", "brand": "Dulux", "description": "Interior low-sheen washable paint.", "in_stock": True, "rating": 4.6, "reviews_count": 145},
            # Furniture
            {"product_id": "p018", "name": "3-Seater Fabric Sofa Charcoal", "category": "Furniture", "price": 1499.0, "original_price": 1899.0, "discount": 21, "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=500&auto=format", "brand": "Nook", "description": "Modern 3-seater with deep cushions.", "in_stock": True, "rating": 4.5, "reviews_count": 27},
            {"product_id": "p019", "name": "Oak Dining Table 6-Seater", "category": "Furniture", "price": 999.0, "original_price": 1299.0, "discount": 23, "image": "https://images.unsplash.com/photo-1449247709967-d4461a6a6103?w=500&auto=format", "brand": "TimberCo", "description": "Solid oak dining table.", "in_stock": True, "rating": 4.7, "reviews_count": 33},
            # Flooring
            {"product_id": "p020", "name": "Vinyl Plank Flooring 2.2m² Oak", "category": "Flooring & Tiles", "price": 79.0, "original_price": 99.0, "discount": 20, "image": "https://images.unsplash.com/photo-1615529182904-14819c35db37?w=500&auto=format", "brand": "FloorMax", "description": "Waterproof vinyl plank, oak look.", "in_stock": True, "rating": 4.5, "reviews_count": 72},
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
