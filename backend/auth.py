import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User

bearer = HTTPBearer(auto_error=False)

def make_token(user_id: int) -> str:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 32 or secret.startswith("replace-"):
        raise RuntimeError("Set a secure JWT_SECRET (32+ characters) in backend/.env")
    return jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, secret, algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise HTTPException(401, "Please log in")
    try:
        data = jwt.decode(credentials.credentials, os.environ["JWT_SECRET"], algorithms=["HS256"])
        user = db.get(User, int(data["sub"]))
        if user is None or not user.is_verified:
            raise ValueError("Invalid user")
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid or expired login")
