from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    nome_completo: str
    nome_exibicao: str | None = None
    papel: str
    estado_referencia_id: str | None = None
    ativo: bool

    class Config:
        from_attributes = True


TokenResponse.model_rebuild()
