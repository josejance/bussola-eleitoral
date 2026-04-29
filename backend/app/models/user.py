from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class PerfilUsuario(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "perfis_usuario"

    email = Column(String(150), unique=True, nullable=False, index=True)
    senha_hash = Column(String(200), nullable=False)
    nome_completo = Column(String(200), nullable=False)
    nome_exibicao = Column(String(100))
    cargo_no_partido = Column(String(150))
    telefone_hash = Column(String(64))
    estado_referencia_id = Column(String(36), ForeignKey("estados.id"))
    papel = Column(String(30), nullable=False, default="leitor_pleno")
    ativo = Column(Boolean, default=True)
    ultimo_acesso = Column(DateTime)
    foto_url = Column(Text)
    configuracoes_json = Column(Text)
    aceite_termo_em = Column(DateTime)
    aceite_termo_versao = Column(String(20))


__all__ = ["PerfilUsuario"]
