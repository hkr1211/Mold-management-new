# alembic/env.py
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- START OF MODIFICATIONS ---
# 这部分是我们的核心修改

# 1. 将项目的根目录添加到Python的模块搜索路径中
#    这样Alembic才能找到位于 `app/utils/models.py` 的模型文件
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# 2. 从我们的 models.py 文件中导入 Base
#    Base 是所有数据表模型的基类，它包含了数据库的“目标结构”
from app.utils.models import Base

# --- 新增：从环境变量手动构建数据库URL ---

def get_url():
    user = os.getenv("POSTGRES_USER", "default_user")
    password = os.getenv("POSTGRES_PASSWORD", "default_password")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "default_db")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"



# --- END OF MODIFICATIONS ---


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- 将我们手动构建的URL设置到Alembic的配置中 ---
config.set_main_option('sqlalchemy.url', get_url())

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- START OF MODIFICATIONS ---
# 3. 将我们的模型元数据(metadata)设置为Alembic的目标
target_metadata = Base.metadata
# --- END OF MODIFICATIONS ---


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 最佳实践：包含命名约定
        render_as_batch=True,
        compare_type=True,
        include_object=lambda obj, name, type_, reflected, compare_to: not (
            type_ == "table" and obj.info.get("skip_autogenerate", False)
        ),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            # 最佳实践：包含命名约定
            render_as_batch=True,
            compare_type=True,
            include_object=lambda obj, name, type_, reflected, compare_to: not (
                type_ == "table" and obj.info.get("skip_autogenerate", False)
            ),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()