from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re

#Registro de Gestores (Novos)
class ManagerCreate(BaseModel):
    nome: str
    cpf: str = Field(..., min_length=11, max_length=14)
    telefone: str = Field(..., min_length=10, max_length=20)
    senha: str
    token: str
    @field_validator('cpf', 'telefone', mode='before')
    @classmethod
    def keep_only_digits(cls, v: str):
        if isinstance(v, str):
            # re.sub(r'\D', '', v) substitui tudo que não for dígito (\D) por vazio ('')
            return re.sub(r'\D', '', v)
        return v

class ManagerResponse(BaseModel):
    id: int
    nome: str
    cpf: str = Field(..., min_length=11, max_length=14)
    telefone: str = Field(..., min_length=10, max_length=20)
    email: EmailStr
    company_id: int

    model_config = {"from_attributes": True}

class ManagerUpdate(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = Field(None, min_length=11, max_length=14)
    telefone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    senha: Optional[str] = None

    @field_validator('cpf', 'telefone', mode='before')
    @classmethod
    def keep_only_digits(cls, v: str):
        if v is None:
            return v
        if isinstance(v, str):
            # re.sub(r'\D', '', v) substitui tudo que não for dígito (\D) por vazio ('')
            return re.sub(r'\D', '', v)
        return v

# --- Uso de licença (para a tela de Colaboradores saber quantas vagas restam) ---
class LicenseUsageResponse(BaseModel):
    max_employees: int
    used_employees: int  # clientes ativos + convites de funcionário pendentes
    max_managers: int
    used_managers: int   # gestores ativos + convites de gestor pendentes
    subscription_active: bool