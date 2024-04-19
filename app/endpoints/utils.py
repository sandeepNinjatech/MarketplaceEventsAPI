import json
import logging
from datetime import datetime
from typing import List

import aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.schemas import EventSchema
from app.pydantic_models.events import GetEventModel


async def get_events_from_redis(redis_key: str, redis_client: aioredis.Redis):
    # Try to get cached data
    logging.info(f"redis key {redis_key}")
    cached_data = await redis_client.get(redis_key)
    if cached_data:
        return cached_data  # Return cached data if available

    return None


async def get_events_from_db(starts_at: datetime, ends_at: datetime, async_session: AsyncSession):
    fetch_events_query = await async_session.execute(
        select(EventSchema).filter(
            EventSchema.start_date_time >= starts_at,
            EventSchema.end_date_time <= ends_at,
        )  # noqa
    )
    events = fetch_events_query.scalars().all()
    return events


async def set_events_in_redis(
    redis_key: str, event_schemas: List[EventSchema], redis_client: aioredis.Redis
):
    redis_events = [
        GetEventModel.model_validate(event_schema).model_dump_json()
        for event_schema in event_schemas
    ]
    try:
        await redis_client.set(redis_key, json.dumps(redis_events))
    except Exception as err:
        logging.error(err)
