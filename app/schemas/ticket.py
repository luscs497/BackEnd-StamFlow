from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.ticket import TicketStatus
from app.models.ticket_message import MessageAuthor

# --- ESTRUTURAS BÁSICAS ---

class TicketMessageSchema(BaseModel):
    id: int
    author_type: MessageAuthor
    content: str
    criado_em: datetime

    model_config = {"from_attributes": True}

# --- CRIAÇÃO E EDIÇÃO ---

class TicketCreate(BaseModel):
    assunto: str
    mensagem_inicial: str

class TicketReply(BaseModel):
    content: str

class TicketUpdateMessage(BaseModel):
    content: str

class TicketUpdateStatus(BaseModel):
    status: TicketStatus

# --- LEITURA (O que o Front recebe) ---

class TicketResponse(BaseModel):
    id: int
    assunto: str
    status: TicketStatus
    criado_em: datetime
    atualizado_em: datetime
    # Lista de mensagens dentro do ticket
    messages: List[TicketMessageSchema] = []

    model_config = {"from_attributes": True}