# main.py
import jwt
from jwt import PyJWTError
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from models import Base, User, Product

# ------------------------------------------
# SETTINGS
# ------------------------------------------
DATABASE_URL = "sqlite:///./products.db"
SECRET_KEY = "CHANGE_THIS_SECRET_KEY"    # IMPORTANT: use env / secure key vault storage in production like kms/azure key vault.
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


# ------------------------------------------
# Utility Helpers
# ------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(*, data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError:
        return None


# ------------------------------------------
# Authentication Dependency
# ------------------------------------------
async def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Invalid Authorization header format")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")

    username: str = payload.get("sub")
    if not username:
        raise HTTPException(401, "Invalid token payload")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(401, "User not found")

    return user


def require_roles(*roles):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "403 Forbidden")
        return user
    return checker


# ------------------------------------------
# Schemas
# ------------------------------------------
class TokenRequest(BaseModel):
    username: str
    expires_minutes: Optional[int] = ACCESS_TOKEN_EXPIRE_MINUTES


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_at: datetime


class ProductIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None


class ProductOut(ProductIn):
    id: int
    class Config:
        from_attributes = True


# ------------------------------------------
# FastAPI App
# ------------------------------------------
app = FastAPI(title="Product Service - FastAPI ")
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )

    # add bearer auth security scheme
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Paste the JWT token here (no `Bearer ` prefix required)."
    }

    # apply globally so the Authorize button is enabled and endpoints will show lock icon
    openapi_schema["security"] = [{"HTTPBearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# ------------------------------------------
# Token Creation Endpoint
# ------------------------------------------
@app.post("/token", response_model=TokenResponse)
def create_token(
    request: TokenRequest,
    caller: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Admin can generate for anyone
    # Others only for themselves
    if caller.role != "admin" and caller.username != request.username:
        raise HTTPException(403, "You can create JWT tokens only for your own account.")

    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(404, "User not found")

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_minutes=request.expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    expires_at = datetime.utcnow() + timedelta(
        minutes=request.expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return TokenResponse(access_token=access_token, role=user.role, expires_at=expires_at)


# ------------------------------------------
# Product Endpoints
# ------------------------------------------
@app.post("/products", response_model=ProductOut)
def add_product(
    p: ProductIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    exists = db.query(Product).filter(Product.name == p.name).first()
    if exists:
        raise HTTPException(409, "Product name must be unique.")

    product = Product(name=p.name, description=p.description, price=p.price)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products", response_model=List[ProductOut])
def get_products(
    user: User = Depends(require_roles("admin", "privileged")),
    db: Session = Depends(get_db),
):
    products = db.query(Product).all()
    if not products:
        raise HTTPException(status_code=200, detail="No products found")
    return products


@app.get("/products/{pid}", response_model=ProductOut)
def get_product(
    pid: int,
    user: User = Depends(require_roles("admin", "privileged")),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == pid).first()
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@app.get("/")
def root():
    return {"status": "running", "service": "Product Service"}