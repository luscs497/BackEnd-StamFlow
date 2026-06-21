from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

from app.models.enterprise_request import EnterpriseRequestStatus


class EnterpriseRequestCreate(BaseModel):
    nome_empresa: str
    contato_nome: str
    contato_email: Optional[EmailStr] = None
    contato_whatsapp: Optional[str] = None
    qtd_colaboradores: int = Field(default=1, ge=1)
    qtd_gestores: int = Field(default=1, ge=1)
    observacoes: Optional[str] = None


class EnterpriseRequestResponse(BaseModel):
    id: int
    nome_empresa: str
    contato_nome: str
    contato_email: Optional[str] = None
    contato_whatsapp: Optional[str] = None
    qtd_colaboradores: int
    qtd_gestores: int
    observacoes: Optional[str] = None
    status: EnterpriseRequestStatus
    company_id: Optional[int] = None
    criado_em: datetime
    model_config = {"from_attributes": True}


class EnterpriseStatusUpdate(BaseModel):
    status: EnterpriseRequestStatus


class EnterpriseProvision(BaseModel):
    company_id: int   # empresa já cadastrada (via /company/register)
    plan_id: int      # plano corporativo
