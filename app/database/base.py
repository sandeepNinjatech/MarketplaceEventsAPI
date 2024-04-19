import aioredis
from sqlalchemy.engine.url import URL

from app.core.config import Config
from app.utils.constants import REDIS


engine_kw = {
    # "echo": False,  # print all SQL statements
    "pool_pre_ping": True,
    # feature will normally emit SQL equivalent to “SELECT 1” each time a connection is checked out from the pool
    "pool_size": 2,  # number of connections to keep open at a time
    "max_overflow": 4,  # number of connections to allow to be opened above pool_size
    "connect_args": {
        "prepared_statement_cache_size": 0,  # disable prepared statement cache
        "statement_cache_size": 0,  # disable statement cache
    },
}


def get_db_url(config: Config) -> URL:
    config_db = config.data["db"]
    return URL.create(drivername="postgresql+asyncpg", **config_db)


def get_redis_client(config: Config) -> aioredis.StrictRedis:
    if config.data["ENVIRONMENT"] == "test":
        return aioredis.Redis(
            host=config.data[REDIS]["host"],
            port=config.data[REDIS]["port"],
            password=config.data[REDIS]["password"],
            encoding="utf-8",
            decode_responses=True,
        )
    return aioredis.StrictRedis.from_url(
        config.data[REDIS]["url"], encoding="utf-8", decode_responses=True
    )
