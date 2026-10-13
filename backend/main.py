import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import Base, engine, get_db
from models import User, EmailOTP, Property
from email_service import send_otp
from auth import current_user, make_token

password_hasher = PasswordHash.recommended()
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Move360 API", lifespan=lifespan)
app.mount("/css", StaticFiles(directory=FRONTEND / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND / "js"), name="js")

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Move360"}

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str = Field(min_length=8, max_length=20)
    location: str = Field(min_length=2, max_length=100)
    rooms: int = Field(ge=1, le=10)
    budget: int = Field(ge=1000, le=100000000)

class OTPIn(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")

class EmailIn(BaseModel):
    email: EmailStr

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class PropertyIn(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    area: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=3, max_length=255)
    rent: int = Field(ge=1000)
    size: int = Field(ge=100)
    rooms: int = Field(ge=1)
    baths: int = Field(ge=1)
    description: str = Field(default="", max_length=3000)

def profile(user: User):
    return {"id": user.id, "name": user.username, "email": user.email, "phone": user.phone,
            "location": user.location, "rooms": user.preferred_rooms, "budget": float(user.budget or 0),
            "landlord": user.role == "landlord", "is_verified": bool(user.is_verified)}

def otp_hash(user_id: int, code: str):
    return hmac.new(os.environ["JWT_SECRET"].encode(), f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()

def issue_otp(db: Session, user: User):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    last = db.scalar(select(EmailOTP).where(EmailOTP.user_id == user.id).order_by(EmailOTP.id.desc()))
    if last and last.created_at and (now - last.created_at).total_seconds() < 60:
        raise HTTPException(429, "Wait 60 seconds before requesting another code")
    code = f"{secrets.randbelow(1000000):06d}"
    record = EmailOTP(user_id=user.id, otp_hash=otp_hash(user.id, code), expires_at=now + timedelta(minutes=5))
    db.add(record)
    db.flush()
    try:
        send_otp(user.email, code)
    except Exception:
        db.rollback()
        raise HTTPException(503, "Could not send email. Check SMTP settings and try again")
    db.commit()

@app.post("/api/auth/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered. Log in or resend OTP")
    user = User(username=data.name, email=email, password_hash=password_hasher.hash(data.password),
                phone=data.phone, location=data.location, preferred_rooms=data.rooms, budget=Decimal(data.budget))
    db.add(user)
    db.commit()
    db.refresh(user)
    issue_otp(db, user)
    return {"message": "Verification code sent to your email"}

@app.post("/api/auth/resend-otp")
def resend(data: EmailIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user and not user.is_verified:
        issue_otp(db, user)
    return {"message": "If an unverified account exists, a code has been sent"}

@app.post("/api/auth/verify-otp")
def verify(data: OTPIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if not user or user.is_verified:
        raise HTTPException(400, "Invalid verification request")
    otp = db.scalar(select(EmailOTP).where(EmailOTP.user_id == user.id).order_by(EmailOTP.id.desc()).with_for_update())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not otp or otp.used or otp.expires_at < now or otp.attempts >= 5:
        raise HTTPException(400, "Code expired or too many attempts. Request a new code")
    otp.attempts += 1
    if not hmac.compare_digest(otp.otp_hash, otp_hash(user.id, data.code)):
        db.commit()
        raise HTTPException(400, "Incorrect verification code")
    otp.used = True
    user.is_verified = True
    db.commit()
    return {"message": "Email verified. You can now log in"}

@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if not user or not password_hasher.verify(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_verified:
        raise HTTPException(403, "Verify your email first")
    return {"access_token": make_token(user.id), "token_type": "bearer", "user": profile(user)}

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return profile(user)

@app.post("/api/auth/landlord")
def landlord(user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.role = "landlord"
    db.commit()
    return profile(user)

@app.get("/api/properties")
def properties(db: Session = Depends(get_db)):
    return [{"id": f"db{p.id}", "ownerId": p.owner_id, "owner": "Verified landlord", "title": p.title,
             "area": p.area, "address": p.address, "rent": p.rent, "size": p.size,
             "rooms": p.rooms, "baths": p.baths, "description": p.description, "emoji": "🏠"}
            for p in db.scalars(select(Property).order_by(Property.id.desc())).all()]

@app.post("/api/properties", status_code=201)
def add_property(data: PropertyIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "landlord":
        raise HTTPException(403, "Activate your landlord profile first")
    p = Property(owner_id=user.id, **data.model_dump())
    db.add(p)
    db.commit()
    return {"message": "Property published", "id": f"db{p.id}"}

@app.delete("/api/properties/{property_id}")
def delete_property(property_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Property, property_id)
    if not p or p.owner_id != user.id:
        raise HTTPException(404, "Property not found")
    db.delete(p)
    db.commit()
    return {"message": "Property deleted"}
