import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from flask import current_app

from alembic import context

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db

config = context.config

fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

target_metadata = db.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    flask_db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=flask_db_uri
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
           process_revision_directives=context.get_x_argument(as_dictionary=True).get('process_revision_directives', lambda rev, context, versions: rev),
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    with app.app_context():
        run_migrations_online()
