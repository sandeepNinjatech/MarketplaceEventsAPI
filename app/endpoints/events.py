import json
import logging
from datetime import datetime

import aioredis
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from app.database.session_manager.db_session import Database
from app.endpoints.dependency import get_async_redis_client
from app.endpoints.utils import get_events_from_db
from app.endpoints.utils import get_events_from_redis
from app.endpoints.utils import set_events_in_redis
from app.pydantic_models.events import ErrorModel
from app.pydantic_models.events import EventModel
from app.pydantic_models.events import ResponseEventModel
from app.pydantic_models.events import StandardResponseModel


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

events_router = APIRouter(
    prefix="/api/v1",
    tags=["events"],
)


@events_router.get("/events", status_code=200, response_model=StandardResponseModel)
async def get_events(
    starts_at: datetime = Query(
        ..., description="Start date for filtering events", example="2020-01-01T00:00:00"
    ),
    ends_at: datetime = Query(
        ..., description="End date for filtering events", example="2024-01-01T00:00:00"
    ),
    redis_client: aioredis.Redis = Depends(get_async_redis_client),
) -> StandardResponseModel:
    """
    Retrieve a list of events filtered by start and end date.
    Cache results in Redis and queries the database if cache miss occurs.
    """
    if ends_at <= starts_at:
        error_msg = "End date must be greater than start date"
        logger.error(error_msg)
        return StandardResponseModel(error=ErrorModel(code="400", message=error_msg))

    redis_key = f"events_{starts_at.isoformat()}_{ends_at.isoformat()}"
    try:
        redis_events_json = await get_events_from_redis(redis_key, redis_client)
        if redis_events_json:
            logger.info(f"Cache hit for key: {redis_key}")
            redis_events = json.loads(redis_events_json)
            event_models = [EventModel.parse_raw(event) for event in redis_events]
            return StandardResponseModel(data=ResponseEventModel(events=event_models))

        logger.info("Cache miss querying database.")
        async with Database() as async_session:
            event_schemas = await get_events_from_db(starts_at, ends_at, async_session)
            if event_schemas:
                await set_events_in_redis(redis_key, event_schemas, redis_client)
                event_models = [
                    EventModel.model_validate(event_schema) for event_schema in event_schemas
                ]
                return StandardResponseModel(data=ResponseEventModel(events=event_models))
            else:
                logger.info("No events found for the specified date range.")
                return StandardResponseModel()
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to process events: {error_msg}")
        return StandardResponseModel(
            error=ErrorModel(code="500", message="Internal server error")
        )
