from common.models import Operator
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import create_access_token, verify_password
from api.deps import get_db
from api.errors import APIError
from api.schemas import LoginRequest, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, session: Session = Depends(get_db)) -> dict:
    operator = session.execute(select(Operator).where(Operator.username == body.username)).scalar_one_or_none()
    if operator is None or not verify_password(body.password, operator.password_hash):
        raise APIError(401, "invalid_credentials", "Incorrect username or password.")
    return {"access_token": create_access_token(operator.id, operator.username), "token_type": "bearer"}
