from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))
from database import get_db
from src.api.models import User
from src.api.schemas import UserCreate, LoginRequest, TokenResponse, UserOut, APIResponse
from src.api.auth_utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "data": UserOut.model_validate(user)}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {
        "success": True,
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": UserOut.model_validate(user),
        },
    }
