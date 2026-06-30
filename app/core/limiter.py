"""
Rate limiter central da aplicação (CORREÇÃO C1).

Antes, a aplicação não tinha NENHUMA proteção contra força bruta no login,
spam em /auth/register, abuso em /auth/forgot-password ou tentativas
repetidas na rota pública /invite/by-token/{token}. Também não havia
limit_req no Nginx. Este módulo introduz um limiter por IP usando slowapi.

A instância é criada aqui (e não no main.py) para poder ser importada tanto
pelo main.py — que registra o middleware e o handler de erro — quanto pelas
rotas que aplicam @limiter.limit(...) em endpoints específicos.

Observação sobre o IP real: como a API roda atrás do Nginx, o IP de origem
chega no header X-Forwarded-For. get_remote_address do slowapi lê
request.client.host, que com o proxy local seria 127.0.0.1 e colocaria todos
no mesmo balde. Por isso usamos uma função que prioriza o primeiro IP de
X-Forwarded-For. Para isso ser confiável, o Nginx DEVE setar esse header
e a API não deve ser acessível por fora do proxy.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For pode ser "cliente, proxy1, proxy2" — o primeiro é a origem.
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# RATE LIMIT GLOBAL (default_limits):
# Teto por IP aplicado AUTOMATICAMENTE a toda requisição da API — inclusive os
# endpoints autenticados (/reports/sync, /tickets, /notifications, etc.) que
# antes não tinham limite individual. Isso fecha o cenário de um cliente logado
# (ou um bug/robô no frontend) martelar a API com dezenas de milhares de
# requisições e degradar a disponibilidade para todos.
#
# Os limites específicos mais restritos (ex.: @limiter.limit("10/minute") no
# /login) continuam valendo e são aplicados ADICIONALMENTE ao global — o mais
# restritivo vence. Ou seja, este default NÃO afrouxa os limites de auth.
#
# Valores escolhidos com folga para uso legítimo:
#   - 300/minute: um usuário ativo no painel (polling de relatórios a cada 30s,
#     notificações, navegação) fica MUITO abaixo disso. 300/min só é atingido
#     por automação/abuso.
#   - 5000/hour: teto de segurança para uso sustentado ao longo do tempo.
# Se algum fluxo legítimo específico estourar isso no futuro, dá para isentá-lo
# com @limiter.exempt na rota.
limiter = Limiter(
    key_func=_client_ip,
    default_limits=["300/minute", "5000/hour"],
)
