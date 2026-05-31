from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional, Any
from app.models.subscription import SubscriptionStatus
from sqlalchemy import inspect as sa_inspect
import re
# Registro de Empresas (Input)
class CompanyCreate(BaseModel):
    nome_fantasia: str
    razao_social: str
    email: EmailStr
    cnpj: str = Field(..., min_length=14, max_length=18)
    telefone: str = Field(..., min_length=10, max_length=20)
    senha: str

    @field_validator('cnpj', 'telefone', mode='before')
    @classmethod
    def keep_only_digits(cls, v: str):
        if isinstance(v, str):
            # re.sub(r'\D', '', v) substitui tudo que não for dígito (\D) por vazio ('')
            return re.sub(r'\D', '', v)
        return v

# Resposta da API (Output)
class CompanyResponse(BaseModel):
    id: int
    nome_fantasia: str
    razao_social: str
    email: EmailStr
    cnpj: str = Field(..., min_length=14, max_length=18)
    telefone: str = Field(..., min_length=10, max_length=20)
    max_gestores: int = 0
    max_funcionarios: int = 0
    
    model_config = {"from_attributes": True}

    @model_validator(mode='before')
    @classmethod
    def get_limits_from_subscription(cls, data: Any):
        # Evita disparar lazy-load da relação 'subscription' em contexto async
        # (causaria MissingGreenlet). Só lê a relação se ela JÁ estiver carregada
        # (ex.: rotas que usam selectinload). Caso contrário, mantém os defaults.
        try:
            state = sa_inspect(data)
            if "subscription" in state.unloaded:
                return data
        except Exception:
            # data não é uma instância ORM (ex.: dict) — segue o fluxo normal
            pass

        subscription = getattr(data, "subscription", None)
        if subscription and subscription.status == SubscriptionStatus.active:
            data.max_gestores = subscription.max_managers_purchased
            data.max_funcionarios = subscription.max_employees_purchased
        return data

class CompanyUpdate(BaseModel):
    nome_fantasia: Optional[str] = None
    razao_social: Optional[str] = None
    email: Optional[EmailStr] = None
    cnpj: Optional[str] = Field(None, min_length=14, max_length=18)
    telefone: Optional[str] = Field(None, min_length=10, max_length=20)
    senha: Optional[str] = None

    @field_validator('cnpj', 'telefone', mode='before')
    @classmethod
    def keep_only_digits(cls, v: str):
        if isinstance(v, str):
            # re.sub(r'\D', '', v) substitui tudo que não for dígito (\D) por vazio ('')
            return re.sub(r'\D', '', v)
        return v