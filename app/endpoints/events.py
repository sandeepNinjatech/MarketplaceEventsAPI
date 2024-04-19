import logging
from datetime import datetime
from http.client import HTTPException  # noqa
from typing import List

from fastapi import APIRouter
from fastapi import Query
from sqlalchemy import select

from app.database.schemas.events import EventSchema
from app.database.session_manager.db_session import Database
from app.pydantic_models.events import GetEventModel


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

events_router = APIRouter(
    prefix="/api/v1",
    tags=["events"],
)


@events_router.get("/events", status_code=200, response_model=List[GetEventModel])
async def get_events(
    starts_at: datetime = Query(..., description="Start date for filtering events"),
    ends_at: datetime = Query(..., description="End date for filtering events"),
):
    if ends_at <= starts_at:
        raise HTTPException(400, "end date should be greater than start date")

    async with Database() as async_session:
        fetch_events_query = await async_session.execute(
            select(EventSchema).filter(
                EventSchema.start_date_time >= starts_at,
                EventSchema.end_date_time <= ends_at,
            )  # noqa
        )
        print("data fetched")
        events = fetch_events_query.scalars().all()
        print(events)
        return events
        # result = [GetEventModel.model_dump(event) for event in events]
        # print(result)
        # return result
