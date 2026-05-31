from pydantic import BaseModel
from typing import Dict, Optional, List, Literal

# ==========================================================
# INPUT: Sincronização (Front -> Backend)
# ==========================================================

class MetricGroup(BaseModel):
    perfeito: int = 0
    bom: int = 0
    ruim: int = 0
    critico: int = 0


class SyncPayload(BaseModel):
    """
    Payload único para /reports/sync
    """
    date: Optional[str] = None

    # Métricas (opcionais)
    shoulder: Optional[MetricGroup] = None
    head: Optional[MetricGroup] = None
    rotation: Optional[MetricGroup] = None
    back: Optional[MetricGroup] = None

    neutral: Optional[MetricGroup] = None
    happy: Optional[MetricGroup] = None
    sad: Optional[MetricGroup] = None
    angry: Optional[MetricGroup] = None

    # Tempo
    tempo_uso_segundos: Optional[int] = None

    # Conquistas (incrementos)
    pausas_mentais_feitas: Optional[int] = None
    exercicios_feitos: Optional[int] = None


# ==========================================================
# INPUT: Incremento dedicado (opcional)
# ==========================================================

class AchievementIncrementPayload(BaseModel):
    category: Literal["mental", "exercicios"]
    date: Optional[str] = None


# ==========================================================
# OUTPUT: DASHBOARD (CLIENTE & GESTOR)
# ==========================================================

class AchievementDay(BaseModel):
    date: str
    pausas_mentais_feitas: int
    exercicios_feitos: int


class AchievementsSummary(BaseModel):
    pausas_mentais_feitas: int
    exercicios_feitos: int


class DistributionData(BaseModel):
    excelente: int
    bom: int
    ruim: int
    critico: int

# --- NOVO: Distribuição Específica de Humor ---
class HumorDistribution(BaseModel):
    happy: int = 0    # Felicidade
    neutral: int = 0  # Neutro
    angry: int = 0    # Raiva
    sad: int = 0      # Tristeza

# --- NOVO: Detalhes Específicos de Ergonomia ---
class ErgonomicDetails(BaseModel):
    shoulder_status: str = "---" # Ombro
    head_status: str = "---"     # Cabeça
    rotation_status: str = "---" # Rotação
    back_status: str = "---"     # Dorso

class DashboardResponse(BaseModel):
    stamina_media: str
    tempo_total_uso: str
    melhor_dia: str
    pior_dia: str

    distribuicao_tempo: DistributionData # Mantido para Stamina Geral
    
    # NOVOS CAMPOS (Opcionais para não quebrar compatibilidade, mas sempre enviados)
    distribuicao_humor: Optional[HumorDistribution] = None
    detalhes_ergonomia: Optional[ErgonomicDetails] = None
    
    tempos_absolutos: Optional[Dict[str, str]] = None

    conquistas_periodo: AchievementsSummary
    conquistas_por_dia: List[AchievementDay]


# ==========================================================
# GESTOR
# ==========================================================

class TeamAchievementsByClient(BaseModel):
    client_id: int
    pausas_mentais_feitas: int
    exercicios_feitos: int


class TeamAchievementsResponse(BaseModel):
    total: AchievementsSummary
    por_cliente: List[TeamAchievementsByClient] = []


class EngagementResponse(BaseModel):
    exercicios_feitos: int = 0
    pausas_mentais_feitas: int = 0
    tickets_total: int = 0


class TeamDashboardResponse(DashboardResponse):
    engajamento: EngagementResponse = EngagementResponse()