import asyncio
import decimal
import logging
from datetime import datetime
from typing import List

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from lxml import etree
from sqlalchemy import select
from sqlalchemy import tuple_
from sqlalchemy.ext.asyncio import AsyncSession

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
    # url = "https://gist.githubusercontent.com/sergio-nespral/82879974d30ddbdc47989c34c8b2b5ed/raw/44785ca73a62694583eb3efa0757db3c1e5292b1/response_1.xml"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.content
        else:
            logging.error(f"Failed to fetch data: {response.status_code}")
            return None


def get_event_id_model_mappings(root):
    base_event_elements = root.findall(".//base_event")
    logging.info(f"total base element {len(base_event_elements)}")
    event_id_model_mappings = {}
    for base_event_element in base_event_elements:
        title = base_event_element.get("title")
        base_event_id = base_event_element.get("base_event_id")
        logging.info(f"Processing base event {title} with ID {base_event_id}")
        if base_event_element.get("sell_mode") == "offline":
            logging.info(f"Skipping offline base event {title}")
            continue

        event_elements = base_event_element.findall(".//event")
        logging.info(f"total {len(event_elements)} elements found ")
        for event_element in event_elements:
            event_id = event_element.get("event_id")
            start_date_time = datetime.fromisoformat(event_element.get("event_start_date"))
            end_date_time = datetime.fromisoformat(event_element.get("event_end_date"))
            prices = [
                decimal.Decimal(zone.get("price")) for zone in event_element.findall(".//zone")
            ]
            min_price = float(min(prices))
            max_price = float(max(prices))
            new_event_model = PostEventModel(
                event_id=event_id,
                base_event_id=base_event_id,
                title=title,
                start_date_time=start_date_time,
                end_date_time=end_date_time,
                min_price=min_price,
                max_price=max_price,
            )
            event_id_model_mappings[f"{base_event_id}_{event_id}"] = new_event_model
            logging.info(
                f"Event {event_id} from base event {base_event_id} processed and mapped."
            )
    return event_id_model_mappings


async def get_events_from_db(event_id_pairs: List[str], async_session: AsyncSession):
    id_pairs = [
        (int(event_id_pair.split("_")[0]), int(event_id_pair.split("_")[1]))
        for event_id_pair in event_id_pairs
    ]
    event_query = await async_session.execute(
        select(EventSchema).filter(
            tuple_(EventSchema.base_event_id, EventSchema.event_id).in_(id_pairs)
        )
    )
    events = event_query.scalars().all()
    return events


async def parse_and_store(xml_data):
    root = etree.fromstring(xml_data)
    async with Database() as async_session:
        event_id_model_mappings = get_event_id_model_mappings(root)
        event_id_pairs = set(event_id_model_mappings.keys())
        event_schemas = await get_events_from_db(event_id_pairs, async_session)

        db_event_id_pairs = {
            f"{event_schema.base_event_id}_{event_schema.event_id}"
            for event_schema in event_schemas
        }
        missing_event_ids = event_id_pairs - db_event_id_pairs
        if missing_event_ids:
            logging.info(f"missing event ids {missing_event_ids}")
        else:
            logging.info("no missing event ids")
        event_schema_list = []

        for event_id_pair in missing_event_ids:
            event_model = event_id_model_mappings[event_id_pair]
            new_event_schema = EventSchema(**event_model.model_dump())
            event_schema_list.append(new_event_schema)
            logging.info(
                f"New event {event_id_pair} added to the session for database insertion."
            )

        if event_schema_list:
            async_session.add_all(event_schema_list)
            await async_session.commit()
            logging.info("All new events have been committed to the database.")
        else:
            logging.info("No new events to add to the database.")


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
