from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# ---------------------------------------------------------
# IMPORTANT
# Import every model/module that contributes tables to
# Base.metadata BEFORE target_metadata is assigned.
# ---------------------------------------------------------

import app.models  # noqa: F401

from app.modules.ai_mentor.models import (  # noqa: F401
    AIConversation,
    AIMessage,
)

from app.modules.notifications.models import (  # noqa: F401
    Notification,
    NotificationType,
)

from app.modules.mentorship.models import (  # noqa: F401
    MentorProfile,
    MentorSkill,
    MentoringMode,
    Mentorship,
    MentorshipStatus,
)

from app.modules.professionals.models import (  # noqa: F401
    ProfessionalProfile,
)

from app.modules.preferences import models as preferences_models  # noqa: F401
from app.modules.daily_assessment import models as daily_assessment_models  # noqa: F401
from app.modules.news import models as news_models  # noqa: F401

# ---------------------------------------------------------
# HACKATHON MODELS
# ---------------------------------------------------------

from app.modules.hackathons import models as hackathon_models  # noqa: F401
from app.modules.messaging import models as messaging_models  # noqa: F401
from app.models import oauth_account  # noqa: F401
from app.models import pending_oauth  # noqa: F401
# ---------------------------------------------------------
# ALEMBIC CONFIG
# ---------------------------------------------------------

config = context.config

config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


# ---------------------------------------------------------
# OFFLINE MIGRATIONS
# ---------------------------------------------------------

def run_migrations_offline() -> None:
    url = config.get_main_option(
        "sqlalchemy.url"
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------
# ONLINE MIGRATIONS
# ---------------------------------------------------------

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()