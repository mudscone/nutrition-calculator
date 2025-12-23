
import os
import secrets
from fastapi import Request, HTTPException

def verify_admin_password(password: str) -> bool:
    expected = os.getenv("ADMIN_PASSWORD", "")
    if not expected:
        # Fail closed: if no password set, admin login should be impossible.
        return False
    # Constant-time comparison
    return secrets.compare_digest(password or "", expected)

def require_admin(request: Request):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin login required")
