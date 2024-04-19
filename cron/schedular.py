import asyncio
import decimal
import logging
from datetime import datetime

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from lxml import etree
from sqlalchemy import select

from app.core.config import get_config
from app.database.base import engine_kw
from app.database.base import get_db_url
from app.database.schemas import EventSchema
from app.database.session_manager.db_session import Database
from app.pydantic_models.events import PostEventModel
from app.utils.constants import ConfigFile


logging.basicConfig(level=logging.INFO)


async def fetch_events():
    url = "https://provider.code-challenge.feverup.com/api/events"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.content
        else:
            logging.error(f"Failed to fetch data: {response.status_code}")
            return None


async def parse_and_store(xml_data):
    root = etree.fromstring(xml_data)
    async with Database() as async_session:
        all_base_elements = root.findall(".//base_event")
        logging.info(f"total base element {len(all_base_elements)}")
        for base_event_element in all_base_elements:
            title = base_event_element.get("title")
            logging.info(f"processing base event {title}")
            if base_event_element.get("sell_mode") == "offline":
                logging.info(f"base event {title} sell mode is offline , hence skipping it")
                continue

            all_elements = base_event_element.findall(".//event")
            logging.info(f"total {len(all_elements)} elements found ")
            for event_element in all_elements:
                event_id = event_element.get("event_id")
                logging.info(f"processing event_id {event_id}")
                # Check if event_id already exists
                event_query = await async_session.execute(
                    select(EventSchema).filter_by(event_id=int(event_id))
                )
                existing_event_schema = event_query.scalars().one_or_none()
                if not existing_event_schema:
                    logging.info(f"event_id {event_id} not found in db")
                    start_date_time = datetime.fromisoformat(
                        event_element.get("event_start_date")
                    )
                    end_date_time = datetime.fromisoformat(event_element.get("event_end_date"))
                    prices = [
                        decimal.Decimal(zone.get("price"))
                        for zone in event_element.findall(".//zone")
                    ]
                    min_price = float(min(prices))
                    max_price = float(max(prices))

                    new_event_model = PostEventModel(
                        event_id=event_id,
                        title=title,
                        start_date_time=start_date_time,
                        end_date_time=end_date_time,
                        min_price=min_price,
                        max_price=max_price,
                    )
                    new_event_schema = EventSchema(**new_event_model.model_dump())
                    async_session.add(new_event_schema)
                    logging.info(f"event_id {event_id} added in db")
                else:
                    logging.info(f"event_id {event_id} found in db, hence skip processing")

            logging.info("\n")


async def main():
    logging.info("start fetching events cron job")
    xml_data = await fetch_events()
    if xml_data:
        await parse_and_store(xml_data)


def start_scheduler():
    scheduler = AsyncIOScheduler()
    # Schedule job_function to be called every 1 minute
    scheduler.add_job(main, trigger=IntervalTrigger(seconds=5), misfire_grace_time=15)
    scheduler.start()


if __name__ == "__main__":
    config = get_config(ConfigFile.TEST)
    async_db_url = get_db_url(config)
    Database.init(async_db_url, engine_kw=engine_kw)
    asyncio.run(main())
