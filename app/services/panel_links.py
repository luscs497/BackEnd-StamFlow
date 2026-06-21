from typing import Any, List, Dict

from app.models.client import Client
from app.models.manager import Manager

# URLs de cada painel (um deploy por subdomínio) — mesmas usadas pelo frontend.
PANEL_URLS = {
    "avulso": "https://painel.stamflow.com.br/",
    "empregado": "https://user.stamflow.com.br/",
    "gestor": "https://gestor.stamflow.com.br/",
}


def panels_for_user(user: Any) -> List[Dict[str, str]]:
    """
    Painéis que a conta tem direito de acessar, no MESMO critério do frontend:
      - manager                       -> Painel do Gestor (gestor.)
      - client COM company_id         -> Painel do Colaborador (user.)
      - client SEM company_id (avulso)-> Painel Individual (painel.)
      - company                       -> nenhum painel próprio
    """
    paineis: List[Dict[str, str]] = []
    if isinstance(user, Manager):
        paineis.append({"nome": "Painel do Gestor", "tipo": "gestor", "url": PANEL_URLS["gestor"]})
    elif isinstance(user, Client):
        if getattr(user, "company_id", None) is not None:
            paineis.append({"nome": "Painel do Colaborador", "tipo": "empregado", "url": PANEL_URLS["empregado"]})
        else:
            paineis.append({"nome": "Painel Individual", "tipo": "avulso", "url": PANEL_URLS["avulso"]})
    return paineis
