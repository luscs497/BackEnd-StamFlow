from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Literal, Optional, List
import re

# --- Login ---
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

# Removemos access_token/refresh_token do corpo da resposta JSON
# Eles irão apenas nos Headers Set-Cookie
class TokenResponse(BaseModel):
    message: str = "Login realizado com sucesso"
    token_type: str = "bearer"

# Refresh agora não precisa enviar token no corpo, pois vem no cookie
class RefreshTokenRequest(BaseModel):
    pass # Corpo vazio, pois o refresh token vem via Cookie

class AuthUser(BaseModel):
    id: int
    email: EmailStr
    user_type: Literal["client", "manager", "company"]
    company_id: Optional[int] = None
    manager_id: Optional[int] = None

    model_config = {"from_attributes": True}

class LoginResponse(BaseModel):
    user: AuthUser
    # tokens removido daqui, pois vai nos cookies
    access_token: str  
    token_type: str = "bearer"
    message: str = "Login realizado com sucesso"

# --- Registro de Clientes (Novos) ---
class ClientCreate(BaseModel):
    nome_completo: Optional[str] = None
    cpf: Optional[str] = Field(None, min_length=11, max_length=14)
    telefone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    senha: str
    token: Optional[str] = None

    @field_validator('cpf', 'telefone', mode='before')
    @classmethod
    def keep_only_digits(cls, v: str):
        if isinstance(v, str):
            # re.sub(r'\D', '', v) substitui tudo que não for dígito (\D) por vazio ('')
            return re.sub(r'\D', '', v)
        return v

class ClientResponse(BaseModel):
    id: int
    nome_completo: Optional[str] = None
    cpf: Optional[str] = Field(None, min_length=11, max_length=14)
    telefone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: EmailStr
    company_id: Optional[int]
    manager_id: Optional[int]
    criado_em: datetime

    model_config = {"from_attributes": True}

class ClientBulkDelete(BaseModel):
    client_ids: List[int]