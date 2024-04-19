import json
import logging
from datetime import datetime
from http.client import HTTPException  # noqa
from typing import List

import aioredis
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import TypeAdapter

from app.database.session_manager.db_session import Database
from app.endpoints.dependency import get_async_redis_client
from app.endpoints.utils import get_events_from_db
from app.endpoints.utils import get_events_from_redis
from app.endpoints.utils import set_events_in_redis
from app.pydantic_models.events import GetEventModel


logging.basicConfig(level=logging.INFO)

events_router = APIRouter(
    prefix="/api/v1",
    tags=["events"],
)


@events_router.get("/events", status_code=200, response_model=List[GetEventModel])
async def get_events(
    starts_at: datetime = Query(..., description="Start date for filtering events"),
    ends_at: datetime = Query(..., description="End date for filtering events"),
    redis_client: aioredis.Redis = Depends(get_async_redis_client),
):
    if ends_at <= starts_at:
        raise HTTPException(400, "end date should be greater than start date")

    redis_key = f"events_{starts_at}_{ends_at}"
    redis_events_json = await get_events_from_redis(redis_key, redis_client)
    if redis_events_json:
        redis_events = json.loads(redis_events_json)
        result = TypeAdapter(List[GetEventModel]).validate_python(
            [json.loads(redis_event) for redis_event in redis_events]
        )
        return result

    async with Database() as async_session:
        event_schemas = await get_events_from_db(starts_at, ends_at, async_session)
        if event_schemas:
            await set_events_in_redis(redis_key, event_schemas, redis_client)
            return [GetEventModel.model_validate(event_schema) for event_schema in event_schemas]
        return []
