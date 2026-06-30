from typing import Any, List, Dict, Optional

from app.models.client import Client
from app.models.manager import Manager

# URLs de cada painel (um deploy por subdomínio) — mesmas usadas pelo frontend.
PANEL_URLS = {
    "avulso": "https://painel.stamflow.com.br/",
    "empregado": "https://user.stamflow.com.br/",
    "gestor": "https://gestor.stamflow.com.br/",
    # CORREÇÃO: painel da versão demo (decisão de produto, 2026-06).
    "demo": "https://demo.stamflow.com.br/",
}


def panels_for_user(user: Any, subscription_status: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Painéis que a conta tem direito de acessar, no MESMO critério do frontend
    (ver components/LegacyBootstrap.tsx em cada projeto):
      - manager                           -> Painel do Gestor (gestor.)
      - client COM company_id             -> Painel do Colaborador (user.)
      - client SEM company_id, status DEMO-> Painel Demo (demo.)
      - client SEM company_id, demais     -> Painel Individual (painel.)
      - company                           -> nenhum painel próprio

    subscription_status: valor de Subscription.status.value (ex.: "DEMO",
    "ACTIVE", "TRIALING"). Passado explicitamente porque este módulo não tem
    acesso à sessão do banco para buscar a subscription por conta própria —
    quem chama (account_service.get_profile) já tem essa informação.
    """
    paineis: List[Dict[str, str]] = []
    if isinstance(user, Manager):
        paineis.append({"nome": "Painel do Gestor", "tipo": "gestor", "url": PANEL_URLS["gestor"]})
    elif isinstance(user, Client):
        if getattr(user, "company_id", None) is not None:
            paineis.append({"nome": "Painel do Colaborador", "tipo": "empregado", "url": PANEL_URLS["empregado"]})
        elif subscription_status == "DEMO":
            paineis.append({"nome": "Painel Demo", "tipo": "demo", "url": PANEL_URLS["demo"]})
        else:
            paineis.append({"nome": "Painel Individual", "tipo": "avulso", "url": PANEL_URLS["avulso"]})
    return paineis
