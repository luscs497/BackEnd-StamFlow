from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.ticket import TicketStatus, ReportTag
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
    tag: ReportTag = ReportTag.operational

class TicketReply(BaseModel):
    content: str

class TicketUpdateMessage(BaseModel):
    content: str

class TicketUpdateStatus(BaseModel):
    status: TicketStatus

class TicketUpdateTag(BaseModel):
    tag: ReportTag

# --- LEITURA (O que o Front recebe) ---

class TicketResponse(BaseModel):
    id: int
    assunto: str
    status: TicketStatus
    tag: ReportTag
    criado_em: datetime
    atualizado_em: datetime
    # Lista de mensagens dentro do ticket
    messages: List[TicketMessageSchema] = []

    model_config = {"from_attributes": True}