# app/services/report_service.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
import json
import csv
import io
from typing import Any, Optional

from app.models.daily_report import DailyReport
from app.schemas.report import (
    SyncPayload,
    DashboardResponse,
    DistributionData,
    AchievementsSummary,
    AchievementDay,
    TeamAchievementsResponse,
    TeamAchievementsByClient,
    HumorDistribution,
    ErgonomicDetails
)

# Imports para PDF (ReportLab)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ReportService:

    # ==========================================================
    # LÓGICA DE SINCRONIZAÇÃO (WRITE)
    # ==========================================================

    @staticmethod
    async def sync_metrics(db: AsyncSession, client_id: int, payload: SyncPayload):
        report_date = date.today()
        payload_date = getattr(payload, "date", None)
        if payload_date:
            try:
                report_date = date.fromisoformat(payload_date)
            except ValueError:
                pass

        query = select(DailyReport).where(
            DailyReport.client_id == client_id,
            DailyReport.report_date == report_date
        )
        result = await db.execute(query)
        report = result.scalars().first()

        if not report:
            report = DailyReport(
                client_id=client_id,
                report_date=report_date,
                metrics={},
                tempo_uso_segundos=0,
                pausas_mentais_feitas=0,
                exercicios_feitos=0,
            )
            db.add(report)
            await db.flush()

        TEMPO_BLOCO_SEGUNDOS = 30
        payload_tempo = getattr(payload, "tempo_uso_segundos", None)
        payload_tem_metrics = ReportService._payload_has_metrics(payload)

        if payload_tempo is not None:
            try:
                inc = int(payload_tempo)
            except Exception:
                inc = 0
            if inc > 0:
                report.tempo_uso_segundos = int(report.tempo_uso_segundos or 0) + inc
        else:
            if payload_tem_metrics:
                report.tempo_uso_segundos = int(report.tempo_uso_segundos or 0) + TEMPO_BLOCO_SEGUNDOS

        inc_pausas = getattr(payload, "pausas_mentais_feitas", None)
        inc_exerc = getattr(payload, "exercicios_feitos", None)

        if inc_pausas is not None:
            try:
                report.pausas_mentais_feitas = int(report.pausas_mentais_feitas or 0) + int(inc_pausas)
            except Exception:
                pass

        if inc_exerc is not None:
            try:
                report.exercicios_feitos = int(report.exercicios_feitos or 0) + int(inc_exerc)
            except Exception:
                pass

        metrics_input = ReportService._build_metrics_input_if_present(payload)

        if metrics_input:
            current_metrics = report.metrics
            if isinstance(current_metrics, str):
                current_metrics = json.loads(current_metrics)

            new_metrics = ReportService._somar_metrics_recursivo(current_metrics, metrics_input)
            report.metrics = new_metrics

        db.add(report)
        await db.commit()
        return {"status": "synced"}

    @staticmethod
    def _payload_has_metrics(payload: SyncPayload) -> bool:
        posture_fields = ["shoulder", "head", "rotation", "back"]
        emotion_fields = ["neutral", "happy", "sad", "angry"]
        for f in posture_fields + emotion_fields:
            if getattr(payload, f, None) is not None:
                return True
        return False

    @staticmethod
    def _build_metrics_input_if_present(payload: SyncPayload) -> dict[str, Any] | None:
        shoulder = getattr(payload, "shoulder", None)
        head = getattr(payload, "head", None)
        rotation = getattr(payload, "rotation", None)
        back = getattr(payload, "back", None)

        neutral = getattr(payload, "neutral", None)
        happy = getattr(payload, "happy", None)
        sad = getattr(payload, "sad", None)
        angry = getattr(payload, "angry", None)

        if all(v is None for v in [shoulder, head, rotation, back, neutral, happy, sad, angry]):
            return None

        metrics: dict[str, Any] = {}
        posture: dict[str, Any] = {}
        emotion: dict[str, Any] = {}

        if shoulder is not None: posture["shoulder"] = shoulder.model_dump()
        if head is not None: posture["head"] = head.model_dump()
        if rotation is not None: posture["rotation"] = rotation.model_dump()
        if back is not None: posture["back"] = back.model_dump()

        if neutral is not None: emotion["neutral"] = neutral.model_dump()
        if happy is not None: emotion["happy"] = happy.model_dump()
        if sad is not None: emotion["sad"] = sad.model_dump()
        if angry is not None: emotion["angry"] = angry.model_dump()

        if posture: metrics["posture"] = posture
        if emotion: metrics["emotion"] = emotion

        return metrics if metrics else None

    @staticmethod
    def _somar_metrics_recursivo(antigas: dict, novas: dict) -> dict:
        resultado = antigas.copy() if isinstance(antigas, dict) else {}
        for k, v in novas.items():
            if k not in resultado:
                resultado[k] = v
            else:
                if isinstance(v, dict) and isinstance(resultado[k], dict):
                    resultado[k] = ReportService._somar_metrics_recursivo(resultado[k], v)
                elif isinstance(v, int) and isinstance(resultado[k], int):
                    resultado[k] += v
        return resultado

    @staticmethod
    async def register_achievement(db: AsyncSession, client_id: int, category: str, payload_date: str | None):
        report_date = date.today()
        if payload_date:
            try:
                report_date = date.fromisoformat(payload_date)
            except ValueError:
                pass

        query = select(DailyReport).where(
            DailyReport.client_id == client_id,
            DailyReport.report_date == report_date
        )
        result = await db.execute(query)
        report = result.scalars().first()

        if not report:
            report = DailyReport(
                client_id=client_id,
                report_date=report_date,
                metrics={},
                tempo_uso_segundos=0,
                pausas_mentais_feitas=0,
                exercicios_feitos=0
            )
            db.add(report)
            await db.flush()

        if category == "mental":
            report.pausas_mentais_feitas = int(report.pausas_mentais_feitas or 0) + 1
        elif category == "exercicios":
            report.exercicios_feitos = int(report.exercicios_feitos or 0) + 1
        else:
            return {"status": "ignored"}

        db.add(report)
        await db.commit()
        return {"status": "ok"}

    # ==========================================================
    # DASHBOARD (READ)
    # ==========================================================

    @staticmethod
    async def get_dashboard_data(
        db: AsyncSession,
        client_ids: list[int],
        start_date: date,
        end_date: date,
        incluir_classificacao_no_ranking: bool = False,
    ) -> DashboardResponse:
        """
        incluir_classificacao_no_ranking: quando True, "melhor_dia"/"pior_dia"
        passam a incluir também o rótulo de classificação do dia
        (ex.: "24/06 (82% — Excelente)"), em vez de só "24/06 (82%)".
        Isolado por flag para não afetar o painel Gestor (/team-dashboard),
        que reusa esta mesma função e ainda espera o formato antigo.
        """

        query = select(DailyReport).where(
            DailyReport.client_id.in_(client_ids),
            DailyReport.report_date >= start_date,
            DailyReport.report_date <= end_date
        ).order_by(DailyReport.report_date.asc())

        result = await db.execute(query)
        reports = result.scalars().all()

        if not reports:
            return ReportService._empty_dashboard()

        metrics_agg: dict = {}
        total_seconds = 0
        total_pausas = 0
        total_exercicios = 0
        conquistas_por_dia: list[AchievementDay] = []
        melhor_dia = {"date": None, "score": -1, "stamina": 0}
        pior_dia = {"date": None, "score": -1, "stamina": 0}

        for report in reports:
            metrics = report.metrics
            if isinstance(metrics, str):
                metrics = json.loads(metrics)

            total_seconds += int(report.tempo_uso_segundos or 0)
            pausas_dia = int(report.pausas_mentais_feitas or 0)
            exercicios_dia = int(report.exercicios_feitos or 0)
            total_pausas += pausas_dia
            total_exercicios += exercicios_dia

            conquistas_por_dia.append(AchievementDay(
                date=report.report_date.isoformat(),
                pausas_mentais_feitas=pausas_dia,
                exercicios_feitos=exercicios_dia
            ))

            metrics_agg = ReportService._somar_metrics_recursivo(metrics_agg, metrics)
            stamina_dia = ReportService._calcular_stamina_0_100(metrics, int(report.tempo_uso_segundos or 0))

            if stamina_dia > melhor_dia["score"]:
                melhor_dia["score"] = stamina_dia
                melhor_dia["date"] = report.report_date
                melhor_dia["stamina"] = stamina_dia

            if pior_dia["score"] == -1 or stamina_dia < pior_dia["score"]:
                pior_dia["score"] = stamina_dia
                pior_dia["date"] = report.report_date
                pior_dia["stamina"] = stamina_dia

        stamina_media = ReportService._calcular_stamina_0_100(metrics_agg, total_seconds)
        distribuicao = ReportService._calcular_distribuicao_percentual(metrics_agg)
        dist_humor = ReportService._calcular_distribuicao_humor(metrics_agg)
        det_ergonomia = ReportService._calcular_detalhes_ergonomia(metrics_agg)

        tempos_abs = None
        if start_date == end_date:
            tempos_abs = ReportService._calcular_tempos_absolutos(metrics_agg, total_seconds)

        formatar_dia = (
            ReportService._formatar_dia_ranking_com_classificacao
            if incluir_classificacao_no_ranking
            else ReportService._formatar_dia_ranking
        )

        return DashboardResponse(
            stamina_media=f"{int(stamina_media)}% {ReportService._get_label_stamina(stamina_media)}",
            tempo_total_uso=ReportService._formatar_tempo(total_seconds),
            melhor_dia=formatar_dia(melhor_dia["date"], melhor_dia["stamina"]),
            pior_dia=formatar_dia(pior_dia["date"], pior_dia["stamina"]),
            distribuicao_tempo=distribuicao,
            distribuicao_humor=dist_humor,
            detalhes_ergonomia=det_ergonomia,
            tempos_absolutos=tempos_abs,
            conquistas_periodo=AchievementsSummary(
                pausas_mentais_feitas=total_pausas,
                exercicios_feitos=total_exercicios
            ),
            conquistas_por_dia=conquistas_por_dia
        )

    # ==========================================================
    # GESTOR / TEAMS
    # ==========================================================

    @staticmethod
    async def get_team_achievements(
        db: AsyncSession,
        company_id: int,
        start_date: date,
        end_date: date
    ) -> TeamAchievementsResponse:

        from app.models.client import Client

        q_clients = select(Client.id).where(Client.company_id == company_id)
        r_clients = await db.execute(q_clients)
        client_ids = r_clients.scalars().all()

        if not client_ids:
            return TeamAchievementsResponse(
                total=AchievementsSummary(pausas_mentais_feitas=0, exercicios_feitos=0),
                por_cliente=[]
            )

        q_reports = select(
            DailyReport.client_id,
            func.coalesce(func.sum(DailyReport.pausas_mentais_feitas), 0).label("pausas"),
            func.coalesce(func.sum(DailyReport.exercicios_feitos), 0).label("exercicios"),
        ).where(
            DailyReport.client_id.in_(client_ids),
            DailyReport.report_date >= start_date,
            DailyReport.report_date <= end_date
        ).group_by(DailyReport.client_id)

        r_reports = await db.execute(q_reports)
        rows = r_reports.all()

        por_cliente: list[TeamAchievementsByClient] = []
        total_pausas = 0
        total_exercicios = 0

        for client_id, pausas, exercicios in rows:
            pausas_i = int(pausas or 0)
            exercicios_i = int(exercicios or 0)
            total_pausas += pausas_i
            total_exercicios += exercicios_i

            por_cliente.append(TeamAchievementsByClient(
                client_id=int(client_id),
                pausas_mentais_feitas=pausas_i,
                exercicios_feitos=exercicios_i
            ))

        return TeamAchievementsResponse(
            total=AchievementsSummary(
                pausas_mentais_feitas=total_pausas,
                exercicios_feitos=total_exercicios
            ),
            por_cliente=por_cliente
        )

    @staticmethod
    async def get_team_dashboard_data(
        db: AsyncSession,
        company_id: int,
        start_date: date,
        end_date: date
    ) -> dict:
        from app.models.client import Client

        q_clients = select(Client.id).where(Client.company_id == company_id)
        r_clients = await db.execute(q_clients)
        client_ids = r_clients.scalars().all()

        base_dashboard: DashboardResponse
        if not client_ids:
            base_dashboard = ReportService._empty_dashboard()
            return {
                **base_dashboard.model_dump(),
                "engajamento": {
                    "exercicios": 0,
                    "pausas_mentais": 0,
                    "reports": 0,
                }
            }

        base_dashboard = await ReportService.get_dashboard_data(
            db=db,
            client_ids=list(client_ids),
            start_date=start_date,
            end_date=end_date
        )

        q_eng = select(
            func.coalesce(func.sum(DailyReport.exercicios_feitos), 0).label("exercicios"),
            func.coalesce(func.sum(DailyReport.pausas_mentais_feitas), 0).label("pausas"),
        ).where(
            DailyReport.client_id.in_(client_ids),
            DailyReport.report_date >= start_date,
            DailyReport.report_date <= end_date
        )
        r_eng = await db.execute(q_eng)
        row = r_eng.first()
        exercicios = int(row.exercicios or 0) if row else 0
        pausas = int(row.pausas or 0) if row else 0

        reports_count = await ReportService._count_company_tickets_in_period(
            db=db,
            company_id=company_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            **base_dashboard.model_dump(),
            "engajamento": {
                "exercicios": exercicios,
                "pausas_mentais": pausas,
                "reports": int(reports_count or 0)
            }
        }

    # ==========================================================
    # EXPORTAÇÃO (CSV / PDF) - REDESENHO
    # ==========================================================

    # Rótulos legíveis das categorias do JSONB `metrics`.
    _PARTES_POSTURA = [
        ("shoulder", "Ombro"),
        ("head", "Cabeça"),
        ("rotation", "Rotação"),
        ("back", "Costas"),
    ]
    _EMOCOES = [
        ("happy", "Feliz"),
        ("neutral", "Neutro"),
        ("sad", "Triste"),
        ("angry", "Irritado"),
    ]
    # Chaves do JSONB (`perfeito/bom/ruim/critico`) são preservadas como
    # identificadores internos para não quebrar dados históricos no banco.
    # Os rótulos exibidos seguem o padrão único do sistema: as 4 faixas de
    # 25% — Crítica (0-24%), Atenção (25-49%), Boa (50-74%), Excelente
    # (75-100%).
    _NIVEIS = [
        ("perfeito", "Excelente"),
        ("bom", "Boa"),
        ("ruim", "Atenção"),
        ("critico", "Crítica"),
    ]

    @staticmethod
    async def get_export_data(
        db: AsyncSession,
        company_id: int,
        start_date: date,
        end_date: date
    ) -> list[dict]:
        """
        Extrai TODOS os dados disponíveis de cada DailyReport da empresa no período.

        Privacidade: o nome real do cliente NUNCA sai daqui. Cada client_id é
        mapeado para um rótulo estável "Colaborador N" dentro do relatório.

        Cada registro retornado contém, além de data/tempo/stamina/pausas/exercícios:
          - score (0-100) e status de cada parte da postura (ombro/cabeça/rotação/costas);
          - distribuição de humor (% feliz/neutro/triste/irritado) e índice de humor;
          - contagem bruta de amostras por categoria/nível (perfeito/bom/ruim/crítico);
          - totais de amostras de postura, humor e gerais.
        """
        from app.models.client import Client

        query = select(DailyReport, DailyReport.client_id).join(
            Client, Client.id == DailyReport.client_id
        ).where(
            Client.company_id == company_id,
            DailyReport.report_date >= start_date,
            DailyReport.report_date <= end_date
        ).order_by(DailyReport.client_id.asc(), DailyReport.report_date.asc())

        result = await db.execute(query)
        rows = result.all()

        # Anonimização estável: 1º client_id que aparece -> "Colaborador 1", etc.
        ordem: list = []
        for _, cid in rows:
            if cid not in ordem:
                ordem.append(cid)
        anon = {cid: f"Colaborador {idx + 1}" for idx, cid in enumerate(ordem)}

        export_data: list[dict] = []
        for report, cid in rows:
            metrics = report.metrics
            if isinstance(metrics, str):
                metrics = json.loads(metrics)
            metrics = metrics or {}

            tempo_seg = int(report.tempo_uso_segundos or 0)
            flat = ReportService._achatar_metrics(metrics)

            # Scores agregados
            postura = ReportService._score_grupo(flat, ["shoulder", "head", "rotation", "back"])
            humor = ReportService._score_grupo(flat, ["happy", "neutral", "sad", "angry"])
            stamina = ReportService._calcular_stamina_0_100(metrics, tempo_seg)
            ergo = ReportService._calcular_detalhes_ergonomia(metrics)
            dist_humor = ReportService._calcular_distribuicao_humor(metrics)

            # Score individual de cada parte da postura
            score_parte = {}
            for key, _label in ReportService._PARTES_POSTURA:
                sc = ReportService._score_categoria(flat[key]) if key in flat else None
                score_parte[key] = int(round(sc)) if sc is not None else None

            # Contagem bruta de amostras (nada do `metrics` é descartado)
            counts = {}
            amostras_postura = 0
            amostras_humor = 0
            for key, _label in ReportService._PARTES_POSTURA + ReportService._EMOCOES:
                c = flat.get(key, {}) or {}
                cat = {nivel: int(c.get(nivel, 0) or 0) for nivel, _ in ReportService._NIVEIS}
                cat_total = sum(cat.values())
                cat["total"] = cat_total
                counts[key] = cat
                if any(key == k for k, _ in ReportService._PARTES_POSTURA):
                    amostras_postura += cat_total
                else:
                    amostras_humor += cat_total

            export_data.append({
                # Identificação / tempo
                "data": report.report_date.strftime("%d/%m/%Y"),
                "data_iso": report.report_date.isoformat(),
                "colaborador": anon.get(cid, "Colaborador"),
                "tempo_uso": ReportService._formatar_tempo(tempo_seg),
                "tempo_seg": tempo_seg,
                # Índices principais
                "stamina": int(stamina),
                "stamina_nivel": ReportService._get_label_stamina(stamina),
                "postura": postura,
                "humor": humor,
                # Postura — score + status por parte
                "ombro_pct": score_parte["shoulder"],
                "cabeca_pct": score_parte["head"],
                "rotacao_pct": score_parte["rotation"],
                "costas_pct": score_parte["back"],
                "ombro": ergo.shoulder_status,
                "cabeca": ergo.head_status,
                "rotacao": ergo.rotation_status,
                "costas": ergo.back_status,
                # Humor — distribuição
                "feliz": dist_humor.happy,
                "neutro": dist_humor.neutral,
                "triste": dist_humor.sad,
                "irritado": dist_humor.angry,
                # Conquistas
                "pausas": int(report.pausas_mentais_feitas or 0),
                "exercicios": int(report.exercicios_feitos or 0),
                # Amostras brutas
                "counts": counts,
                "amostras_postura": amostras_postura,
                "amostras_humor": amostras_humor,
                "amostras_total": amostras_postura + amostras_humor,
            })

        return export_data

    # ----------------------------------------------------------
    # Helpers de score / agregação
    # ----------------------------------------------------------

    @staticmethod
    def _score_categoria(counts: dict):
        """
        Score 0-100 de uma categoria a partir das contagens de amostras.

        Pesos = ponto médio da faixa de cada nível (faixas de 25% cada):
            critico   →  12  (faixa 0-24,  Crítica)
            ruim      →  37  (faixa 25-49, Atenção)
            bom       →  62  (faixa 50-74, Boa)
            perfeito  →  87  (faixa 75-100, Excelente)

        Assim, uma categoria com 100% de amostras "bom" pontua 62 → cai em
        "Boa" (consistente). Antes, com peso 75, ela caía em "Excelente".
        """
        total = sum(int(v or 0) for v in counts.values()) if counts else 0
        if total == 0:
            return None
        return (
            int(counts.get("perfeito", 0) or 0) * 87 +
            int(counts.get("bom", 0) or 0) * 62 +
            int(counts.get("ruim", 0) or 0) * 37 +
            int(counts.get("critico", 0) or 0) * 12
        ) / total

    @staticmethod
    def _score_grupo(flat: dict, keys: list):
        vals = []
        for k in keys:
            if k in flat:
                sc = ReportService._score_categoria(flat[k])
                if sc is not None:
                    vals.append(sc)
        if not vals:
            return None
        return int(round(sum(vals) / len(vals)))

    @staticmethod
    def _media_lista(valores: list):
        vals = [v for v in valores if v is not None]
        return int(round(sum(vals) / len(vals))) if vals else None

    @staticmethod
    def _build_aggregates(data: list[dict]) -> tuple[list[dict], dict]:
        """
        A partir dos registros, calcula:
          - por_colaborador: médias e totais de cada colaborador;
          - resumo_equipe: médias, totais e distribuição geral da equipe.
        """
        # ---- Por colaborador ----
        grupos: dict[str, list[dict]] = {}
        for r in data:
            grupos.setdefault(r["colaborador"], []).append(r)

        por_colaborador: list[dict] = []
        for nome, regs in grupos.items():
            tempo_seg = sum(int(x.get("tempo_seg", 0)) for x in regs)
            melhor = max(regs, key=lambda x: x["stamina"])
            pior = min(regs, key=lambda x: x["stamina"])
            por_colaborador.append({
                "colaborador": nome,
                "registros": len(regs),
                "tempo_seg": tempo_seg,
                "tempo_uso": ReportService._formatar_tempo(tempo_seg),
                "stamina": ReportService._media_lista([x["stamina"] for x in regs]) or 0,
                "postura": ReportService._media_lista([x["postura"] for x in regs]),
                "humor": ReportService._media_lista([x["humor"] for x in regs]),
                "pausas": sum(int(x["pausas"]) for x in regs),
                "exercicios": sum(int(x["exercicios"]) for x in regs),
                "melhor_dia": f'{melhor["data"]} ({melhor["stamina"]}%)',
                "pior_dia": f'{pior["data"]} ({pior["stamina"]}%)',
            })
        por_colaborador.sort(key=lambda x: x["colaborador"])

        # ---- Resumo geral da equipe ----
        tempo_total = sum(int(r.get("tempo_seg", 0)) for r in data)
        n_colab = len(grupos)

        # Distribuição de humor agregada (ponderada pelas amostras de humor)
        emo_acc = {k: 0 for k, _ in ReportService._EMOCOES}
        for r in data:
            for k, _ in ReportService._EMOCOES:
                emo_acc[k] += int(r["counts"][k]["total"])
        emo_total = sum(emo_acc.values())
        dist_humor_eq = {
            k: (int(round(emo_acc[k] / emo_total * 100)) if emo_total else 0)
            for k, _ in ReportService._EMOCOES
        }

        # Melhor / pior colaborador por stamina média
        melhor_colab = max(por_colaborador, key=lambda x: x["stamina"]) if por_colaborador else None
        pior_colab = min(por_colaborador, key=lambda x: x["stamina"]) if por_colaborador else None

        stamina_eq = ReportService._media_lista([r["stamina"] for r in data]) or 0
        resumo_equipe = {
            "n_colaboradores": n_colab,
            "n_registros": len(data),
            "tempo_total_seg": tempo_total,
            "tempo_total": ReportService._formatar_tempo(tempo_total),
            "tempo_medio_colab": ReportService._formatar_tempo(int(tempo_total / n_colab)) if n_colab else "0s",
            "stamina_media": stamina_eq,
            "stamina_nivel": ReportService._get_label_stamina(stamina_eq),
            "postura_media": ReportService._media_lista([r["postura"] for r in data]),
            "humor_media": ReportService._media_lista([r["humor"] for r in data]),
            "pausas_total": sum(int(r["pausas"]) for r in data),
            "exercicios_total": sum(int(r["exercicios"]) for r in data),
            "amostras_total": sum(int(r["amostras_total"]) for r in data),
            "dist_humor": dist_humor_eq,
            "melhor_colaborador": (
                f'{melhor_colab["colaborador"]} ({melhor_colab["stamina"]}%)' if melhor_colab else "--"
            ),
            "pior_colaborador": (
                f'{pior_colab["colaborador"]} ({pior_colab["stamina"]}%)' if pior_colab else "--"
            ),
        }
        return por_colaborador, resumo_equipe

    # ----------------------------------------------------------
    # CSV (simples, porém completo e organizado)
    # ----------------------------------------------------------

    @staticmethod
    def generate_csv(data: list[dict]) -> str:
        por_colaborador, resumo = ReportService._build_aggregates(data)

        output = io.StringIO()
        output.write("\ufeff")  # BOM p/ o Excel abrir acentos corretamente
        writer = csv.writer(output, delimiter=";")

        def n(v):
            return v if v is not None else "-"

        # ---- Cabeçalho do relatório ----
        writer.writerow(["StamFlow - Relatório de Produtividade da Equipe"])
        writer.writerow(["Dados anonimizados para preservar a privacidade dos colaboradores"])
        writer.writerow([])

        # ---- Seção 1: Resumo geral da equipe ----
        writer.writerow(["RESUMO GERAL DA EQUIPE"])
        writer.writerow(["Métrica", "Valor"])
        writer.writerow(["Colaboradores", resumo["n_colaboradores"]])
        writer.writerow(["Registros (dia x colaborador)", resumo["n_registros"]])
        writer.writerow(["Stamina média (%)", resumo["stamina_media"]])
        writer.writerow(["Nível de stamina", resumo["stamina_nivel"]])
        writer.writerow(["Postura média (%)", n(resumo["postura_media"])])
        writer.writerow(["Índice de humor (%)", n(resumo["humor_media"])])
        writer.writerow(["Tempo ativo total", resumo["tempo_total"]])
        writer.writerow(["Tempo médio por colaborador", resumo["tempo_medio_colab"]])
        writer.writerow(["Pausas mentais (total)", resumo["pausas_total"]])
        writer.writerow(["Exercícios (total)", resumo["exercicios_total"]])
        writer.writerow(["Amostras coletadas (total)", resumo["amostras_total"]])
        writer.writerow(["Humor - Feliz (%)", resumo["dist_humor"]["happy"]])
        writer.writerow(["Humor - Neutro (%)", resumo["dist_humor"]["neutral"]])
        writer.writerow(["Humor - Triste (%)", resumo["dist_humor"]["sad"]])
        writer.writerow(["Humor - Irritado (%)", resumo["dist_humor"]["angry"]])
        writer.writerow(["Melhor colaborador (stamina média)", resumo["melhor_colaborador"]])
        writer.writerow(["Colaborador em atenção (stamina média)", resumo["pior_colaborador"]])
        writer.writerow([])

        # ---- Seção 2: Resumo por colaborador ----
        writer.writerow(["RESUMO POR COLABORADOR"])
        writer.writerow([
            "Colaborador", "Registros", "Tempo ativo", "Stamina média (%)",
            "Postura média (%)", "Humor médio (%)", "Pausas mentais", "Exercícios",
            "Melhor dia", "Pior dia",
        ])
        for c in por_colaborador:
            writer.writerow([
                c["colaborador"], c["registros"], c["tempo_uso"], c["stamina"],
                n(c["postura"]), n(c["humor"]), c["pausas"], c["exercicios"],
                c["melhor_dia"], c["pior_dia"],
            ])
        writer.writerow([])

        # ---- Seção 3: Detalhamento por registro ----
        writer.writerow(["DETALHAMENTO POR REGISTRO"])
        writer.writerow([
            "Data", "Colaborador", "Tempo de uso", "Tempo (s)",
            "Stamina (%)", "Nível stamina", "Postura média (%)", "Índice humor (%)",
            "Ombro (%)", "Ombro", "Cabeça (%)", "Cabeça",
            "Rotação (%)", "Rotação", "Costas (%)", "Costas",
            "Feliz (%)", "Neutro (%)", "Triste (%)", "Irritado (%)",
            "Pausas mentais", "Exercícios",
            "Amostras postura", "Amostras humor", "Amostras totais",
        ])
        for r in data:
            writer.writerow([
                r["data"], r["colaborador"], r["tempo_uso"], r["tempo_seg"],
                r["stamina"], r["stamina_nivel"], n(r["postura"]), n(r["humor"]),
                n(r["ombro_pct"]), r["ombro"], n(r["cabeca_pct"]), r["cabeca"],
                n(r["rotacao_pct"]), r["rotacao"], n(r["costas_pct"]), r["costas"],
                r["feliz"], r["neutro"], r["triste"], r["irritado"],
                r["pausas"], r["exercicios"],
                r["amostras_postura"], r["amostras_humor"], r["amostras_total"],
            ])
        writer.writerow([])

        # ---- Seção 4: Amostras brutas por categoria/nível ----
        # Tudo que existe no campo `metrics` é exposto aqui, sem perdas.
        writer.writerow(["AMOSTRAS BRUTAS POR CATEGORIA (do campo metrics)"])
        writer.writerow([
            "Data", "Colaborador", "Categoria", "Tipo",
            "Excelente", "Boa", "Atenção", "Crítica", "Total",
        ])
        cat_labels = (
            [(k, lbl, "Postura") for k, lbl in ReportService._PARTES_POSTURA] +
            [(k, lbl, "Humor") for k, lbl in ReportService._EMOCOES]
        )
        for r in data:
            for key, lbl, tipo in cat_labels:
                c = r["counts"][key]
                writer.writerow([
                    r["data"], r["colaborador"], lbl, tipo,
                    c["perfeito"], c["bom"], c["ruim"], c["critico"], c["total"],
                ])

        return output.getvalue()

    # ----------------------------------------------------------
    # PDF (tema escuro StamFlow)
    # ----------------------------------------------------------

    @staticmethod
    def _load_logo():
        """
        Baixa o logo do StamFlow (cache em memória). Se a rede falhar,
        retorna None e o PDF usa o wordmark vetorial como fallback.
        """
        cached = getattr(ReportService, "_logo_cache", "unset")
        if cached != "unset":
            return cached

        logo = None
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://login.stamflow.com.br/icon.png",
                headers={"User-Agent": "StamFlow-Report/1.0"},
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw = resp.read()
            if raw:
                logo = io.BytesIO(raw)
        except Exception:
            logo = None

        ReportService._logo_cache = logo
        return logo

    @staticmethod
    def generate_pdf(data: list[dict], start_date: date, end_date: date) -> bytes:
        from reportlab.platypus import Image
        from reportlab.lib.utils import ImageReader

        por_colaborador, resumo = ReportService._build_aggregates(data)

        # ---- Paleta StamFlow (tema escuro, refinada) ----
        BG = colors.HexColor("#0b1120")        # fundo
        PANEL = colors.HexColor("#0f172a")     # cartões / cabeçalho de tabela
        ZEBRA = colors.HexColor("#0d182b")     # linha alternada (bem sutil)
        HAIR = colors.HexColor("#1e293b")      # linhas finas
        TXT = colors.HexColor("#e2e8f0")       # texto principal
        MUT = colors.HexColor("#94a3b8")       # rótulos
        FAINT = colors.HexColor("#64748b")     # rodapé / dicas
        ACCENT = colors.HexColor("#34d399")    # único destaque (verde)
        WHITE = colors.HexColor("#f8fafc")

        GRAD = ["#38bdf8", "#a855f7", "#ec4899", "#f59e0b"]  # raio — só uma fita fina no topo

        PAGE_W, PAGE_H = A4
        L_MARGIN = R_MARGIN = 40
        CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN

        logo = ReportService._load_logo()

        def draw_chrome(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(BG)
            canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            # fina assinatura de marca no topo (3 pt)
            seg = PAGE_W / len(GRAD)
            for idx, c in enumerate(GRAD):
                canvas.setFillColor(colors.HexColor(c))
                canvas.rect(idx * seg, PAGE_H - 3, seg + 1, 3, fill=1, stroke=0)
            # rodapé discreto, com linha fina acima
            canvas.setStrokeColor(HAIR)
            canvas.setLineWidth(0.5)
            canvas.line(L_MARGIN, 40, PAGE_W - R_MARGIN, 40)
            canvas.setFillColor(FAINT)
            canvas.setFont("Helvetica", 7.5)
            canvas.drawString(L_MARGIN, 28, "Gerado automaticamente pelo StamFlow")
            canvas.drawCentredString(PAGE_W / 2, 28, "Dados anonimizados para preservar a privacidade")
            canvas.drawRightString(PAGE_W - R_MARGIN, 28, f"Página {doc.page}")
            canvas.restoreState()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=48, bottomMargin=54, leftMargin=L_MARGIN, rightMargin=R_MARGIN,
            title="Relatório StamFlow", author="StamFlow",
        )
        elements = []

        title_style = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=18, textColor=WHITE, leading=22)
        sub_style = ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, textColor=MUT, leading=13)
        sec_style = ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=11.5, textColor=TXT, leading=15)
        sec_hint = ParagraphStyle("sech", fontName="Helvetica", fontSize=8, textColor=FAINT, leading=11)

        def fmt_pct(v):
            return f"{v}%" if v is not None else "—"

        # ---------- Cabeçalho (logo + título) ----------
        head_txt = [
            Paragraph("StamFlow", title_style),
            Paragraph("Relatório de Produtividade da Equipe", sub_style),
            Paragraph(
                f"Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}",
                sub_style,
            ),
        ]
        if logo is not None:
            try:
                logo.seek(0)
                iw, ih = ImageReader(logo).getSize()
                disp_h = 40.0
                disp_w = disp_h * (iw / ih) if ih else 40.0
                logo.seek(0)
                img = Image(logo, width=disp_w, height=disp_h)
                header = Table(
                    [[img, head_txt]],
                    colWidths=[disp_w + 14, CONTENT_W - disp_w - 14],
                )
                header.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                elements.append(header)
            except Exception:
                elements.extend(head_txt)
        else:
            elements.extend(head_txt)

        elements.append(Spacer(1, 20))

        # ---------- Cartões de resumo (KPIs) — monocromáticos, 1 destaque ----------
        def kpi_table(rows_pairs, accent_idx=()):
            """rows_pairs: lista de (label, valor); 4 por linha. accent_idx destaca em verde."""
            labels = [p[0] for p in rows_pairs]
            values = [p[1] for p in rows_pairs]
            tbl = Table([labels, values], colWidths=[CONTENT_W / 4.0] * 4)
            st = [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("TEXTCOLOR", (0, 0), (-1, 0), MUT),
                ("TEXTCOLOR", (0, 1), (-1, 1), WHITE),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("FONTSIZE", (0, 1), (-1, 1), 13),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
                ("TOPPADDING", (0, 1), (-1, 1), 1),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 11),
                ("LINEAFTER", (0, 0), (-2, -1), 0.5, HAIR),
            ]
            for ci in accent_idx:
                st.append(("TEXTCOLOR", (ci, 1), (ci, 1), ACCENT))
            tbl.setStyle(TableStyle(st))
            return tbl

        elements.append(kpi_table(
            [
                ("COLABORADORES", str(resumo["n_colaboradores"])),
                ("STAMINA MÉDIA", f'{resumo["stamina_media"]}%'),
                ("POSTURA MÉDIA", fmt_pct(resumo["postura_media"])),
                ("ÍNDICE DE HUMOR", fmt_pct(resumo["humor_media"])),
            ],
            accent_idx=(1,),  # só a stamina média recebe destaque
        ))
        elements.append(Spacer(1, 8))
        elements.append(kpi_table(
            [
                ("TEMPO ATIVO TOTAL", resumo["tempo_total"]),
                ("MÉDIA / COLABORADOR", resumo["tempo_medio_colab"]),
                ("PAUSAS MENTAIS", str(resumo["pausas_total"])),
                ("EXERCÍCIOS", str(resumo["exercicios_total"])),
            ],
        ))
        elements.append(Spacer(1, 22))

        # ---------- Helpers de tabela limpa (sem grade fechada) ----------
        def clean_style(nrows, extra=None):
            st = [
                ("BACKGROUND", (0, 0), (-1, 0), PANEL),
                ("TEXTCOLOR", (0, 0), (-1, 0), MUT),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 1), (-1, -1), TXT),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, HAIR),
                ("LINEBELOW", (0, 1), (-1, -2), 0.25, HAIR),
            ]
            for ridx in range(2, nrows, 2):
                st.append(("BACKGROUND", (0, ridx), (-1, ridx), ZEBRA))
            if extra:
                st.extend(extra)
            return st

        # ---------- Distribuição de humor da equipe ----------
        elements.append(Paragraph("Distribuição de humor da equipe", sec_style))
        elements.append(Spacer(1, 8))
        dh = resumo["dist_humor"]
        ht = Table(
            [
                ["Feliz", "Neutro", "Triste", "Irritado"],
                [f'{dh["happy"]}%', f'{dh["neutral"]}%', f'{dh["sad"]}%', f'{dh["angry"]}%'],
            ],
            colWidths=[CONTENT_W / 4.0] * 4,
        )
        ht.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PANEL),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUT),
            ("TEXTCOLOR", (0, 1), (-1, 1), TXT),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("FONTSIZE", (0, 1), (-1, 1), 12),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
            ("TOPPADDING", (0, 1), (-1, 1), 1),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
            ("LINEAFTER", (0, 0), (-2, -1), 0.5, HAIR),
        ]))
        elements.append(ht)
        elements.append(Spacer(1, 22))

        # ---------- Resumo por colaborador ----------
        elements.append(Paragraph("Resumo por colaborador", sec_style))
        elements.append(Paragraph("Médias e totais consolidados de cada colaborador no período.", sec_hint))
        elements.append(Spacer(1, 8))

        colab_header = ["Colaborador", "Reg.", "Tempo ativo", "Stamina", "Postura", "Humor", "Pausas", "Exerc."]
        colab_tbl = [colab_header]
        for c in por_colaborador:
            colab_tbl.append([
                c["colaborador"], str(c["registros"]), c["tempo_uso"],
                f'{c["stamina"]}%', fmt_pct(c["postura"]), fmt_pct(c["humor"]),
                str(c["pausas"]), str(c["exercicios"]),
            ])
        ct = Table(colab_tbl, colWidths=[126, 40, 86, 60, 58, 52, 50, 48], repeatRows=1)
        ct.setStyle(TableStyle(clean_style(
            len(colab_tbl),
            extra=[("TEXTCOLOR", (3, 1), (3, -1), ACCENT)],  # stamina em verde (único destaque)
        )))
        elements.append(ct)
        elements.append(Spacer(1, 22))

        # ---------- Detalhamento por registro ----------
        elements.append(Paragraph("Detalhamento por registro", sec_style))
        elements.append(Spacer(1, 8))

        header = ["Colaborador", "Data", "Tempo", "Stamina", "Postura", "Humor", "Pausas", "Exerc."]
        table_data = [header]
        for r in data:
            table_data.append([
                r["colaborador"], r["data"], r["tempo_uso"],
                f'{r["stamina"]}%', fmt_pct(r["postura"]), fmt_pct(r["humor"]),
                str(r["pausas"]), str(r["exercicios"]),
            ])
        t = Table(table_data, colWidths=[118, 70, 66, 58, 58, 52, 48, 46], repeatRows=1)
        t.setStyle(TableStyle(clean_style(
            len(table_data),
            extra=[("TEXTCOLOR", (3, 1), (3, -1), ACCENT)],
        )))
        elements.append(t)
        elements.append(Spacer(1, 22))

        # ---------- Ergonomia e humor por registro ----------
        elements.append(Paragraph("Ergonomia e humor por registro", sec_style))
        elements.append(Paragraph(
            "Status de cada parte do corpo e distribuição de humor (% do tempo) por registro.",
            sec_hint,
        ))
        elements.append(Spacer(1, 8))

        header2 = ["Colaborador", "Ombro", "Cabeça", "Rotação", "Costas",
                   "Feliz", "Neutro", "Triste", "Irritado"]
        table2 = [header2]
        for r in data:
            table2.append([
                r["colaborador"],
                r.get("ombro") or "—", r.get("cabeca") or "—",
                r.get("rotacao") or "—", r.get("costas") or "—",
                f'{r["feliz"]}%', f'{r["neutro"]}%', f'{r["triste"]}%', f'{r["irritado"]}%',
            ])
        t2 = Table(table2, colWidths=[104, 56, 56, 56, 54, 46, 50, 46, 52], repeatRows=1)
        t2.setStyle(TableStyle(clean_style(len(table2))))
        elements.append(t2)

        doc.build(elements, onFirstPage=draw_chrome, onLaterPages=draw_chrome)
        buffer.seek(0)
        return buffer.read()

    # ==========================================================
    # HELPERS DE CÁLCULO / AUXILIARES
    # ==========================================================
    
    @staticmethod
    def _get_ticket_date_column(TicketModel):
        for attr in ("atualizado_em", "criado_em", "created_at", "updated_at"):
            if hasattr(TicketModel, attr):
                return getattr(TicketModel, attr)
        return None

    @staticmethod
    async def _count_company_tickets_in_period(
        db: AsyncSession,
        company_id: int,
        start_date: date,
        end_date: date
    ) -> int:
        try:
            from app.models.ticket import Ticket
        except Exception:
            return 0

        date_col = ReportService._get_ticket_date_column(Ticket)

        if date_col is None:
            q = select(func.count(Ticket.id)).where(Ticket.company_id == company_id)
            r = await db.execute(q)
            return int(r.scalar() or 0)

        q = select(func.count(Ticket.id)).where(
            Ticket.company_id == company_id,
            date_col >= start_date,
            date_col <= end_date
        )
        r = await db.execute(q)
        return int(r.scalar() or 0)

    @staticmethod
    def _calcular_stamina_0_100(metrics: dict, total_seconds: int) -> float:
        """
        Stamina geral (0-100) = 70% postura + 30% emoção.

        Os pesos por nível de amostra são os pontos médios das 4 faixas de
        25% (87/62/37/12), em escala 0..1 aqui. Veja _score_categoria.
        """
        if total_seconds == 0:
            return 0

        flat = ReportService._achatar_metrics(metrics)
        score_postura = 0
        valid_postura = 0
        score_emocao = 0
        valid_emocao = 0

        postura_keys = ['shoulder', 'head', 'rotation', 'back']
        for k in postura_keys:
            if k in flat:
                counts = flat[k]
                total_k = sum(counts.values())
                if total_k > 0:
                    val = (
                        counts.get('perfeito', 0) * 0.87 +
                        counts.get('bom', 0) * 0.62 +
                        counts.get('ruim', 0) * 0.37 +
                        counts.get('critico', 0) * 0.12
                    ) / total_k
                    score_postura += val
                    valid_postura += 1

        emocao_keys = ['happy', 'neutral', 'sad', 'angry']
        for k in emocao_keys:
            if k in flat:
                counts = flat[k]
                total_k = sum(counts.values())
                if total_k > 0:
                    val = (
                        counts.get('perfeito', 0) * 0.87 +
                        counts.get('bom', 0) * 0.62 +
                        counts.get('ruim', 0) * 0.37 +
                        counts.get('critico', 0) * 0.12
                    ) / total_k
                    score_emocao += val
                    valid_emocao += 1

        avg_postura = (score_postura / valid_postura * 100) if valid_postura > 0 else 0
        avg_emocao = (score_emocao / valid_emocao * 100) if valid_emocao > 0 else 0

        return (avg_postura * 0.7) + (avg_emocao * 0.3)

    @staticmethod
    def _calcular_distribuicao_percentual(metrics: dict) -> DistributionData:
        flat = ReportService._achatar_metrics(metrics)
        totals = {"perfeito": 0, "bom": 0, "ruim": 0, "critico": 0}
        grand_total = 0

        for _, counts in flat.items():
            for label, qtd in counts.items():
                if label in totals:
                    totals[label] += qtd
                    grand_total += qtd

        if grand_total == 0:
            return DistributionData(excelente=0, bom=0, ruim=0, critico=0)

        return DistributionData(
            excelente=int((totals["perfeito"] / grand_total) * 100),
            bom=int((totals["bom"] / grand_total) * 100),
            ruim=int((totals["ruim"] / grand_total) * 100),
            critico=int((totals["critico"] / grand_total) * 100)
        )

    @staticmethod
    def _calcular_distribuicao_humor(metrics: dict) -> HumorDistribution:
        flat = ReportService._achatar_metrics(metrics)
        counts = {"happy": 0, "neutral": 0, "angry": 0, "sad": 0}
        grand_total = 0

        for emo_key in counts.keys():
            if emo_key in flat:
                qtd = sum(flat[emo_key].values())
                counts[emo_key] += qtd
                grand_total += qtd
        
        if grand_total == 0:
            return HumorDistribution()

        return HumorDistribution(
            happy=int((counts["happy"] / grand_total) * 100),
            neutral=int((counts["neutral"] / grand_total) * 100),
            angry=int((counts["angry"] / grand_total) * 100),
            sad=int((counts["sad"] / grand_total) * 100)
        )

    @staticmethod
    def _calcular_detalhes_ergonomia(metrics: dict) -> ErgonomicDetails:
        """
        Status textual de cada parte do corpo, no mesmo padrão de 4 faixas
        de 25% usado em toda a aplicação:
            Excelente: 75-100%   Boa: 50-74%
            Atenção:   25-49%    Crítica: 0-24%
        Pesos por amostra = pontos médios das faixas (87/62/37/12).
        """
        flat = ReportService._achatar_metrics(metrics)
        parts_map = {
            "shoulder": "shoulder_status",
            "head": "head_status",
            "rotation": "rotation_status",
            "back": "back_status"
        }
        result = {}

        for part_key, result_key in parts_map.items():
            if part_key not in flat:
                result[result_key] = "---"
                continue
            
            data = flat[part_key]
            total = sum(data.values())
            
            if total == 0:
                result[result_key] = "---"
            else:
                score = (
                    data.get('perfeito', 0) * 87 +
                    data.get('bom', 0) * 62 +
                    data.get('ruim', 0) * 37 +
                    data.get('critico', 0) * 12
                ) / total
                
                if score >= 75: label = "Excelente"
                elif score >= 50: label = "Boa"
                elif score >= 25: label = "Atenção"
                else: label = "Crítica"
                
                result[result_key] = label

        return ErgonomicDetails(**result)

    @staticmethod
    def _calcular_tempos_absolutos(metrics: dict, total_seconds: int) -> dict:
        dist = ReportService._calcular_distribuicao_percentual(metrics)
        def fmt(pct):
            secs = total_seconds * (pct / 100)
            return ReportService._formatar_tempo(int(secs))

        return {
            "excelente": fmt(dist.excelente),
            "bom": fmt(dist.bom),
            "ruim": fmt(dist.ruim),
            "critico": fmt(dist.critico)
        }

    @staticmethod
    def _achatar_metrics(metrics: dict) -> dict:
        flat = {}
        if isinstance(metrics, dict):
            if "posture" in metrics and isinstance(metrics["posture"], dict):
                for k, v in metrics["posture"].items():
                    flat[k] = v
            if "emotion" in metrics and isinstance(metrics["emotion"], dict):
                for k, v in metrics["emotion"].items():
                    flat[k] = v
        return flat

    @staticmethod
    def _formatar_tempo(segundos: int) -> str:
        if segundos < 60:
            return f"{segundos}s"
        mins = segundos // 60
        if mins < 60:
            return f"{mins} min"
        hours = mins // 60
        rem_mins = mins % 60
        return f"{hours}h {rem_mins}min"

    @staticmethod
    def _formatar_dia_ranking(d: date, stamina: float) -> str:
        if not d:
            return "--"
        return f"{d.strftime('%d/%m')} ({int(stamina)}%)"

    @staticmethod
    def _formatar_dia_ranking_com_classificacao(d: date, stamina: float) -> str:
        """
        Mesmo formato de _formatar_dia_ranking, mas inclui a classificação
        do dia (Crítica/Atenção/Boa/Excelente) dentro dos parênteses.
        Usada apenas pelos painéis avulso/user (aba Relatórios), e não pelo
        Gestor, que continua usando _formatar_dia_ranking sem alteração.
        Ex.: "24/06 (82% — Excelente)"
        """
        if not d:
            return "--"
        label = ReportService._get_label_stamina(stamina)
        return f"{d.strftime('%d/%m')} ({int(stamina)}% — {label})"

    @staticmethod
    def _get_label_stamina(val: float) -> str:
        """
        Rótulo textual da stamina segundo o padrão único de 4 faixas de 25%:
            Excelente: 75-100%   Boa: 50-74%
            Atenção:   25-49%    Crítica: 0-24%
        """
        if val >= 75: return "Excelente"
        if val >= 50: return "Boa"
        if val >= 25: return "Atenção"
        return "Crítica"

    @staticmethod
    def _empty_dashboard() -> DashboardResponse:
        return DashboardResponse(
            stamina_media="--",
            tempo_total_uso="0 min",
            melhor_dia="--",
            pior_dia="--",
            distribuicao_tempo=DistributionData(excelente=0, bom=0, ruim=0, critico=0),
            distribuicao_humor=HumorDistribution(),
            detalhes_ergonomia=ErgonomicDetails(),
            tempos_absolutos={"excelente": "0m", "bom": "0m", "ruim": "0m", "critico": "0m"},
            conquistas_periodo=AchievementsSummary(pausas_mentais_feitas=0, exercicios_feitos=0),
            conquistas_por_dia=[]
        )