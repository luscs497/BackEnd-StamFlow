"""
Middleware de proteção CSRF — double-submit cookie pattern (CORREÇÃO C3).

CONTEXTO
--------
Os cookies de sessão do StamFlow usam samesite="lax", necessário para que o
cookie de domínio .stamflow.com.br atravesse a navegação entre subdomínios
(login. → user./gestor./painel.). Mas samesite="lax" não bloqueia todas as
requisições cross-site: em particular, não bloqueia POSTs iniciados via
JavaScript de um frame/worker em outro domínio.

Sem um token CSRF, um site malicioso poderia (em teoria) executar mutações
autenticadas contra a API — desde que o navegador da vítima esteja logado no
StamFlow e o browser envie o cookie junto.

SOLUÇÃO — double-submit cookie
-------------------------------
1. No login/refresh, o backend emite um cookie adicional "csrf_token":
   - NÃO httponly (JS dos painéis legítimos pode lê-lo)
   - Mesmo domínio (.stamflow.com.br), mesmo samesite="lax"
   - Valor: token aleatório seguro (secrets.token_urlsafe(32))

2. O frontend lê esse cookie e, em toda chamada que não seja GET/HEAD/OPTIONS,
   injeta o valor no header "X-CSRF-Token".

3. Este middleware verifica:
   - Se o método for de mutação (POST/PUT/PATCH/DELETE): o header deve existir
     e bater com o cookie.
   - Se não bater: 403 Forbidden.

Por que isso funciona:
   Um atacante cross-site consegue disparar o request com o cookie (via
   samesite=lax + navegação), mas NÃO consegue ler o valor do cookie csrf_token
   (Same-Origin Policy bloqueia JS de outro domínio lendo cookies do domínio
   alvo). Sem saber o valor, não consegue montar o header correto.

ROTAS ISENTAS
-------------
- Qualquer GET, HEAD, OPTIONS (sem mutação de estado)
- /auth/login, /auth/forgot-password, /auth/reset-password (pré-autenticação)
- /auth/refresh (o próprio mecanismo de renovação do csrf_token)
- /webhook/* (autenticado por HMAC, não por cookie)
"""
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Métodos que mutam estado e portanto requerem validação CSRF
CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Rotas isentas — pré-autenticação ou autenticadas por outro mecanismo
CSRF_EXEMPT_PREFIXES = (
    "/auth/login",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/refresh",
    "/auth/register",
    "/webhook",
    # CORREÇÃO: /demo/signup é pré-autenticação (cria conta nova, ainda não
    # existe cookie de sessão/csrf_token nesse momento) — mesmo motivo de
    # /auth/register estar isento.
    "/demo",
)


def generate_csrf_token() -> str:
    """Gera um token CSRF criptograficamente seguro."""
    return secrets.token_urlsafe(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Só aplica em métodos de mutação
        if request.method not in CSRF_PROTECTED_METHODS:
            return await call_next(request)

        # Rotas isentas
        path = request.url.path
        if any(path.startswith(prefix) for prefix in CSRF_EXEMPT_PREFIXES):
            return await call_next(request)

        # Lê o cookie csrf_token (enviado pelo browser junto com os cookies de sessão)
        csrf_cookie = request.cookies.get("csrf_token")

        # Lê o header X-CSRF-Token (enviado pelo JS do painel legítimo)
        csrf_header = request.headers.get("X-CSRF-Token")

        if not csrf_cookie or not csrf_header:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token ausente."},
            )

        # Comparação segura contra timing attacks
        if not secrets.compare_digest(csrf_cookie, csrf_header):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token inválido."},
            )

        return await call_next(request)
