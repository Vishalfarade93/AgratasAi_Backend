from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database.db import get_db
from models.sqp_model import Seller
from core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request Schemas ───────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    brand_name: str = None


class LoginRequest(BaseModel):
    email: str
    password: str


# ── Register ─────────────────────────────────────────────────────

@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new seller account.
    Password is hashed before storing — never stored as plain text.
    """

    # Check if email already exists
    existing = db.query(Seller).filter(Seller.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please login instead."
        )

    # Hash password before storing
    hashed = hash_password(request.password)

    # Create seller
    seller = Seller(
        name=request.name,
        email=request.email,
        password=hashed,
        brand_name=request.brand_name
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)

    # Auto login after register — return token immediately
    token = create_access_token(seller_id=seller.id, email=seller.email)

    return {
        "success": True,
        "message": "Account created successfully",
        "seller_id": seller.id,
        "name": seller.name,
        "brand_name": seller.brand_name,
        "token": token
    }


# ── Login ─────────────────────────────────────────────────────────

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns JWT token valid for 24 hours.
    """

    # Find seller by email
    seller = db.query(Seller).filter(Seller.email == request.email).first()

    # Check email exists and password matches
    if not seller or not verify_password(request.password, seller.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    # Generate token
    token = create_access_token(seller_id=seller.id, email=seller.email)

    return {
        "success": True,
        "message": "Login successful",
        "seller_id": seller.id,
        "name": seller.name,
        "brand_name": seller.brand_name,
        "token": token
    }


# ── Me (get current seller info) ─────────────────────────────────

@router.get("/me")
def get_me(db: Session = Depends(get_db),
           credentials: str = None):
    """
    Get current logged in seller profile.
    Protected route — requires token.
    """
    from fastapi import Request
    from core.dependencies import get_current_seller
    from fastapi.security import HTTPAuthorizationCredentials
    pass