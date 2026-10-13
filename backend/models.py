from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20))
    location = Column(String(100))
    preferred_rooms = Column(Integer)
    budget = Column(Numeric(10, 2))
    role = Column(String(20), default="tenant", nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class EmailOTP(Base):
    __tablename__ = "email_otps"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    otp_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Property(Base):
    __tablename__ = "properties"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(180), nullable=False)
    area = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    rent = Column(Integer, nullable=False)
    size = Column(Integer, nullable=False)
    rooms = Column(Integer, nullable=False)
    baths = Column(Integer, nullable=False)
    description = Column(Text)
