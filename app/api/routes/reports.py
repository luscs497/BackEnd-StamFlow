# app/api/routes/reports.py

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_client, get_current_manager
from app.models.client import Client
from app.models.manager import Manager

from app.schemas.report import (
    SyncPayload,
    DashboardResponse,
    AchievementIncrementPayload,
    TeamAchievementsResponse,
    TeamDashboardResponse,
)

from app.services.report_service import ReportService

router = APIRouter()


# ==============================================================================
# CLIENTE → SINCRONIZAÇÃO
# ==============================================================================
@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_metrics(
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: SyncPayload,
):
    return await ReportService.sync_metrics(
        db=db,
        client_id=current_client.id,
        payload=payload,
    )


# ==============================================================================
# CLIENTE → REGISTRO DE CONQUISTA
# ==============================================================================
@router.post("/achievement", status_code=status.HTTP_200_OK)
async def register_achievement(
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: AchievementIncrementPayload,
):
    return await ReportService.register_achievement(
        db=db,
        client_id=current_client.id,
        category=payload.category,
        payload_date=payload.date,
    )


# ==============================================================================
# CLIENTE → DASHBOARD INDIVIDUAL
# ==============================================================================
@router.get("/dashboard", response_model=DashboardResponse)
async def get_my_dashboard(
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    return await ReportService.get_dashboard_data(
        db=db,
        client_ids=[current_client.id],
        start_date=start_date,
        end_date=end_date,
    )


# ==============================================================================
# GESTOR → DASHBOARD DA EQUIPE
# ==============================================================================
@router.get("/team-dashboard", response_model=TeamDashboardResponse)
async def get_team_dashboard(
    current_manager: Annotated[Manager, Depends(get_current_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    return await ReportService.get_team_dashboard_data(
        db=db,
        company_id=current_manager.company_id,
        start_date=start_date,
        end_date=end_date,
    )


# ==============================================================================
# GESTOR → CONQUISTAS DA EQUIPE
# ==============================================================================
@router.get("/team-achievements", response_model=TeamAchievementsResponse)
async def get_team_achievements(
    current_manager: Annotated[Manager, Depends(get_current_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    return await ReportService.get_team_achievements(
        db=db,
        company_id=current_manager.company_id,
        start_date=start_date,
        end_date=end_date,
    )

# ==============================================================================
# GESTOR → EXPORTAR RELATÓRIO (CSV/PDF) - NOVO!
# ==============================================================================
@router.get("/export")
async def export_reports(
    start_date: date,
    end_date: date,
    current_manager: Annotated[Manager, Depends(get_current_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("csv", pattern="^(csv|pdf)$"),
):
    """
    Exporta relatórios da equipe em CSV ou PDF.
    Apenas Gestores podem acessar.
    """
    
    # 1. Busca os dados brutos
    data = await ReportService.get_export_data(
        db=db,
        company_id=current_manager.company_id,
        start_date=start_date,
        end_date=end_date
    )

    # Sem dados no periodo -> 404 com mensagem clara para o frontend
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum dado encontrado para o período selecionado."
        )

    if format == "csv":
        csv_content = ReportService.generate_csv(data)
        
        response = StreamingResponse(
            iter([csv_content]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f"attachment; filename=relatorio_stamflow_{start_date}_{end_date}.csv"
        return response

    elif format == "pdf":
        pdf_content = ReportService.generate_pdf(data, start_date, end_date)
        
        response = Response(content=pdf_content, media_type="application/pdf")
        response.headers["Content-Disposition"] = f"attachment; filename=relatorio_stamflow_{start_date}_{end_date}.pdf"
        return response