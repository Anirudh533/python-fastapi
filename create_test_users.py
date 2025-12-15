# create_users.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User
import hashlib

DATABASE_URL = "sqlite:///./products.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def create_tables():
    Base.metadata.create_all(bind=engine)

def create_user(username: str, role: str, password: str = "test123"):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if u:
            print(f"{username} already exists")
            return
        user = User(
            username=username,
            role=role,
            hashed_password=hash_password(password)
        )
        db.add(user)
        db.commit()
        print(f"Created: {username} ({role})")
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
    ###Test Users for different roles based on scenarios given.
    ###In Production, it is recommended to test in a more secure way.
    create_user("admin", "admin")
    create_user("alice", "privileged")
    create_user("bob", "nonadmin")