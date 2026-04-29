from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PerfilUsuario
from app.services.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> PerfilUsuario:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")
    data = decode_token(token)
    if not data or "sub" not in data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    user = db.query(PerfilUsuario).filter(PerfilUsuario.id == data["sub"]).first()
    if not user or not user.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inválido ou inativo")
    return user


def require_role(*allowed: str):
    def checker(user: PerfilUsuario = Depends(get_current_user)) -> PerfilUsuario:
        if user.papel not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente")
        return user

    return checker
