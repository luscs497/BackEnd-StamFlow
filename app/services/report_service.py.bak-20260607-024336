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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

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
        end_date: date
    ) -> DashboardResponse:

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

        return DashboardResponse(
            stamina_media=f"{int(stamina_media)}% {ReportService._get_label_stamina(stamina_media)}",
            tempo_total_uso=ReportService._formatar_tempo(total_seconds),
            melhor_dia=ReportService._formatar_dia_ranking(melhor_dia["date"], melhor_dia["stamina"]),
            pior_dia=ReportService._formatar_dia_ranking(pior_dia["date"], pior_dia["stamina"]),
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
    # EXPORTAÇÃO (CSV / PDF) - NOVO!
    # ==========================================================

    @staticmethod
    async def get_export_data(
        db: AsyncSession,
        company_id: int,
        start_date: date,
        end_date: date
    ) -> list[dict]:
        from app.models.client import Client
        
        # Busca dados e faz join com o nome do cliente
        query = select(DailyReport, Client.nome_completo).join(
            Client, Client.id == DailyReport.client_id
        ).where(
            Client.company_id == company_id,
            DailyReport.report_date >= start_date,
            DailyReport.report_date <= end_date
        ).order_by(DailyReport.report_date.desc())

        result = await db.execute(query)
        rows = result.all()

        export_data = []
        for report, nome in rows:
            metrics = report.metrics
            if isinstance(metrics, str): metrics = json.loads(metrics)
            
            stamina = ReportService._calcular_stamina_0_100(metrics, int(report.tempo_uso_segundos or 0))
            tempo_fmt = ReportService._formatar_tempo(int(report.tempo_uso_segundos or 0))

            export_data.append({
                "data": report.report_date.strftime("%d/%m/%Y"),
                "colaborador": nome,
                "tempo_uso": tempo_fmt,
                "stamina": int(stamina),
                "pausas": int(report.pausas_mentais_feitas or 0),
                "exercicios": int(report.exercicios_feitos or 0)
            })
        
        return export_data

    @staticmethod
    def generate_csv(data: list[dict]) -> str:
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';') # CSV para Excel em PT-BR
        
        # Cabeçalho
        writer.writerow(["Data", "Colaborador", "Tempo de Uso", "Stamina (%)", "Pausas Mentais", "Exercícios"])
        
        for row in data:
            writer.writerow([
                row["data"],
                row["colaborador"],
                row["tempo_uso"],
                row["stamina"],
                row["pausas"],
                row["exercicios"]
            ])
            
        return output.getvalue()

    @staticmethod
    def generate_pdf(data: list[dict], start_date: date, end_date: date) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Título
        title = f"Relatório de Produtividade StamFlow"
        period = f"Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Paragraph(period, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Dados da Tabela
        table_data = [["Data", "Colaborador", "Tempo", "Stamina", "Pausas", "Exerc."]]
        
        for row in data:
            table_data.append([
                row["data"],
                row["colaborador"],
                row["tempo_uso"],
                f"{row['stamina']}%",
                str(row["pausas"]),
                str(row["exercicios"])
            ])

        # Estilo da Tabela
        t = Table(table_data, colWidths=[70, 160, 70, 60, 60, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#10B981")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(t)
        
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"Gerado automaticamente pelo sistema StamFlow.", styles['Italic']))

        doc.build(elements)
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
                        counts.get('perfeito', 0) * 1.0 +
                        counts.get('bom', 0) * 0.75 +
                        counts.get('ruim', 0) * 0.35
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
                        counts.get('perfeito', 0) * 1.0 +
                        counts.get('bom', 0) * 0.75 +
                        counts.get('ruim', 0) * 0.35
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
                    data.get('perfeito', 0) * 100 +
                    data.get('bom', 0) * 75 +
                    data.get('ruim', 0) * 35 +
                    data.get('critico', 0) * 0
                ) / total
                
                if score >= 80: label = "Excelente"
                elif score >= 60: label = "Boa"
                elif score >= 30: label = "Atenção"
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
    def _get_label_stamina(val: float) -> str:
        if val >= 75: return "Excelente"
        if val >= 50: return "Bom"
        if val >= 25: return "Ruim"
        return "Crítico"

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