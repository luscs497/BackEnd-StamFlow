from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class DemoSignupRequest(BaseModel):
    """
    Cadastro da versão DEMO (7 dias, limitada, decisão de produto de 2026-06).

    Schema isolado do ClientCreate (usado pelo cadastro avulso normal e pelo
    fluxo de convite) porque aqui o CPF é OBRIGATÓRIO — é o único freio real
    contra contas demo ilimitadas, já que não se pede cartão de crédito. A
    constraint UNIQUE em clients.cpf garante "1 demo por CPF" no nível do
    banco; demo_used_at garante "1 demo por conta" (não reinicia a mesma
    conta). Os dois juntos fecham o caso de reuso.
    """
    nome_completo: str = Field(..., min_length=2, max_length=100)
    cpf: str = Field(..., min_length=11, max_length=14)
    email: EmailStr
    senha: str = Field(..., min_length=8)

    @field_validator("cpf", mode="before")
    @classmethod
    def keep_only_digits(cls, v: str):
        if isinstance(v, str):
            return re.sub(r"\D", "", v)
        return v

    @field_validator("cpf")
    @classmethod
    def validate_cpf_length(cls, v: str):
        if len(v) != 11:
            raise ValueError("CPF deve conter 11 dígitos.")
        return v
