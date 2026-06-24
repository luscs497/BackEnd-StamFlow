from fastapi import APIRouter, Depends, status, BackgroundTasks, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List, Any
from app.db.session import get_db
from app.services.invite_service import InviteService
from app.schemas.invite import (
    InviteCreate,
    InviteResponse,
    InviteUpdate,
    InviteBulkDelete,
    InvitePublicPreview
)
from app.api.deps import get_current_user
router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_invite(background_tasks: BackgroundTasks, db: Annotated[AsyncSession, Depends(get_db)], request: InviteCreate, current_user: Annotated[Any, Depends(get_current_user)]):
    new_invite = await InviteService.send_invite(db, request, current_user, background_tasks)
    return new_invite

@router.post("/register/bulk", status_code=status.HTTP_201_CREATED)
async def register_invites_bulk(
    background_tasks: BackgroundTasks, 
    db: Annotated[AsyncSession, Depends(get_db)], 
    requests: List[InviteCreate],
    current_user: Annotated[Any, Depends(get_current_user)]
):
    return await InviteService.send_invites_bulk(db, requests, current_user, background_tasks)

@router.delete("/bulk", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invites_bulk(
    db: Annotated[AsyncSession, Depends(get_db)], 
    data: InviteBulkDelete,
    current_user: Annotated[Any, Depends(get_current_user)]
):
    await InviteService.delete_invites_bulk(db, current_user, data.invite_ids)

@router.get("/invites", response_model=List[InviteResponse])
async def get_all_invites(db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[Any, Depends(get_current_user)]):
    return await InviteService.get_all_invites(db, current_user)

@router.get("/by-token/{token}", response_model=InvitePublicPreview)
async def get_invite_preview_by_token(db: Annotated[AsyncSession, Depends(get_db)], token: str):
    """
    Rota PÚBLICA (sem autenticação) usada pela página de criação de conta
    (registerEmployee.html) para mostrar o e-mail do convidado e validar o
    link antes do envio do formulário de cadastro.
    """
    return await InviteService.get_invite_preview_by_token(db, token)

@router.get("/{invite_id}", response_model=InviteResponse)
async def get_invite(db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[Any, Depends(get_current_user)], invite_id: int):
    return await InviteService.get_invite(db, current_user, invite_id)
    
@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invite(db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[Any, Depends(get_current_user)], invite_id: int):
    await InviteService.delete_invite(db, current_user, invite_id)

@router.post("/upload")
async def upload_csv(db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[Any, Depends(get_current_user)], background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    return await InviteService.invite_csv(db, user, background_tasks, file)