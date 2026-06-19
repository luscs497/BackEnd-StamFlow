import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ==================================================================================
# 1. CONFIGURAÇÃO DE PATH (Para o Alembic achar seu projeto)
# ==================================================================================
# Adiciona o diretório pai (raiz do projeto) ao path do Python
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# ==================================================================================
# 2. IMPORTAÇÃO DOS MODELOS (Para o Autogenerate funcionar)
# ==================================================================================
# Tenta importar a Base. Se der erro, tenta no outro caminho comum.
try:
    from app.db.base import Base
except ImportError:
    try:
        from app.db.session import Base
    except ImportError:
        print("ERRO: Não foi possível encontrar 'Base'. Verifique se está em app.db.base ou app.db.session")
        raise

# IMPORTANTE: Importar TODOS os modelos aqui para serem registrados na metadata
from app.models.company import Company
from app.models.client import Client
from app.models.manager import Manager
from app.models.client_token import ClientToken
from app.models.client_achievement import ClientAchievement
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.daily_report import DailyReport
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.webhook import WebhookLog
from app.models.invite import Invite
from app.models.enterprise_request import EnterpriseRequest

# Importa as configurações centralizadas (lê o .env)
from app.core.config import settings

# ==================================================================================
# 3. CONFIGURAÇÕES PADRÃO DO ALEMBIC
# ==================================================================================
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ==================================================================================
# URL DO BANCO A PARTIR DO .ENV
# ==================================================================================
# A aplicação usa o driver assíncrono (asyncpg), mas o Alembic roda de forma
# síncrona. Convertemos o driver para psycopg2 antes de injetar na config.
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql+asyncpg"):
    db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

config.set_main_option("sqlalchemy.url", db_url)

# Define o alvo da metadata para a Base do SQLAlchemy
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # Ajuda a detectar mudanças de tipo de coluna
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True, # Ajuda a detectar mudanças de tipo de coluna
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()