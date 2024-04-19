import json
import logging
from datetime import datetime

import aioredis
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

from app.database.session_manager.db_session import Database
from app.endpoints.dependency import get_async_redis_client
from app.endpoints.utils import get_events_from_db
from app.endpoints.utils import get_events_from_redis
from app.endpoints.utils import set_events_in_redis
from app.pydantic_models.events import EventModel
from app.pydantic_models.events import ResponseDataModel
from app.pydantic_models.events import ResponseEventModel


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

events_router = APIRouter(
    prefix="/api/v1",
    tags=["events"],
)


@events_router.get("/events", status_code=200, response_model=ResponseDataModel)
async def get_events(
    starts_at: datetime = Query(..., description="Start date for filtering events"),
    ends_at: datetime = Query(..., description="End date for filtering events"),
    redis_client: aioredis.Redis = Depends(get_async_redis_client),
) -> ResponseDataModel:
    """

    Retrieve a list of events filtered by start and end date.
    Cache results in Redis and queries the database if cache miss occurs.

    Args:
        starts_at (datetime): Start date and time for the events query.
        ends_at (datetime): End date and time for the events query.
        redis_client (aioredis.Redis): Redis client dependency to manage cache operations.

    Raises:
        HTTPException: If the end date is earlier than or the same as the start date.

    Returns:
        ResponseDataModel: A list of events fitting the provided timeframe.
    """
    if ends_at <= starts_at:
        logger.error("End date must be greater than the start date.")
        raise HTTPException(status_code=400, detail="End date should be greater than start date")

    redis_key = f"events_{starts_at.isoformat()}_{ends_at.isoformat()}"
    redis_events_json = await get_events_from_redis(redis_key, redis_client)

    if redis_events_json:
        logger.info(f"Cache hit for key: {redis_key}")
        redis_events = json.loads(redis_events_json)

        event_models = [EventModel.parse_raw(event) for event in redis_events]
        return ResponseDataModel(data=ResponseEventModel(events=event_models))

    logger.info("Cache miss querying database.")
    async with Database() as async_session:
        event_schemas = await get_events_from_db(starts_at, ends_at, async_session)
        if event_schemas:
            await set_events_in_redis(redis_key, event_schemas, redis_client)
            event_models = [
                EventModel.model_validate(event_schema) for event_schema in event_schemas
            ]
            return ResponseDataModel(data=ResponseEventModel(events=event_models))
        else:
            logger.info("No events found for the specified date range.")
            return []
