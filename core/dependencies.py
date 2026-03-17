from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from database.db import get_db
from models.sqp_model import Seller
from core.security import decode_access_token

# This tells FastAPI to look for "Bearer <token>" in the Authorization header
bearer_scheme = HTTPBearer()


def get_current_seller(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Seller:
    """
    Dependency used on every protected route.
    Extracts token from header → decodes it → returns seller object.

    Usage in route:
        def my_route(seller: Seller = Depends(get_current_seller)):
            # seller.id is available here automatically
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please login again.",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = decode_access_token(credentials.credentials)
        seller_id: int = payload.get("seller_id")

        if seller_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Fetch seller from database
    seller = db.query(Seller).filter(Seller.id == seller_id).first()

    if seller is None:
        raise credentials_exception

    return seller