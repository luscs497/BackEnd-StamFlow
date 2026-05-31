from pydantic import BaseModel
from typing import Dict, Optional, List, Literal

class DistributionData(BaseModel):
    excelente: int
    bom: int
    ruim: int
    critico: int

class AchievementDay(BaseModel):
    date: str
    pausas_mentais_feitas: int
    exercicios_feitos: int

class AchievementsSummary(BaseModel):
    pausas_mentais_feitas: int
    exercicios_feitos: int

class DashboardResponse(BaseModel):
    stamina_media: str
    tempo_total_uso: str
    melhor_dia: str
    pior_dia: str

    distribuicao_tempo: DistributionData
    tempos_absolutos: Optional[Dict[str, str]] = None

    conquistas_periodo: AchievementsSummary
    conquistas_por_dia: List[AchievementDay]

# -------------------------
# GESTOR (opcional, separado)
# -------------------------
class EngagementResponse(BaseModel):
    exercicios_feitos: int = 0
    pausas_mentais_feitas: int = 0
    tickets_total: int = 0  # se você usa isso no front

class TeamDashboardResponse(DashboardResponse):
    engajamento: EngagementResponse = EngagementResponse()
