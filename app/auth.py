import hashlib
import secrets

from sqlalchemy.orm import Session

from app import models


SESSIONS: dict[str, int] = {}

def hash_password(password: str) -> str:
    """Hash passwords with a per-user salt for lightweight local auth."""
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}:{digest}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash or ":" not in stored_hash:
        return False
    salt, digest = stored_hash.split(":", 1)
    candidate = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(candidate, digest)


def create_session(student_id: int) -> str:
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = student_id
    return token


def get_student_from_token(token: str | None, db: Session) -> models.Student | None:
    if not token or token not in SESSIONS:
        return None
    return db.query(models.Student).filter(models.Student.id == SESSIONS[token]).first()


def logout_token(token: str | None):
    if token:
        SESSIONS.pop(token, None)
