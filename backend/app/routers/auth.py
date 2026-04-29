from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PerfilUsuario
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.deps import get_current_user
from app.services.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(PerfilUsuario).filter(PerfilUsuario.email == payload.email).first()
    if not user or not verify_password(payload.senha, user.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    if not user.ativo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Conta inativa")

    user.ultimo_acesso = datetime.utcnow()
    db.commit()

    token = create_access_token(subject=user.id, role=user.papel)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(user: PerfilUsuario = Depends(get_current_user)):
    return UserResponse.model_validate(user)
