from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from app.models.invite import InviteRole, InviteStatus

class InviteCreate(BaseModel):
    email: EmailStr
    role: InviteRole

class InviteResponse(BaseModel):
    id: int
    email: EmailStr
    role: InviteRole
    status: InviteStatus
    created_at: datetime
    expires_at: datetime
    token: str
    company_id: int
    manager_id: Optional[int] = None

    model_config = {"from_attributes": True}

class InviteUpdate(BaseModel):
    status: Optional[InviteStatus] = None

class InviteBulkDelete(BaseModel):
    invite_ids: List[int]