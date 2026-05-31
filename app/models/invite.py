from sqlalchemy import Column, ForeignKey, String, BigInteger, DateTime, Enum, func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class InviteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    refused = "refused"

class InviteRole(str, enum.Enum):
    manager = "manager"
    employee = "employee"

class Invite(Base):
    __tablename__ = "invites"

    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(String(100), nullable=False)
    role = Column(Enum(InviteRole, name="invite_role", native_enum=True), nullable=False)
    status = Column(Enum(InviteStatus, name="invite_status", native_enum=True), nullable=False, default=InviteStatus.pending)
    # description = Column(String(300), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    token = Column(String(255), nullable=False, unique=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    manager_id = Column(BigInteger, ForeignKey("managers.id", ondelete="CASCADE"), nullable=True)