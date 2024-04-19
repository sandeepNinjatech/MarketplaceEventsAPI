from fastapi import APIRouter


health_router = APIRouter(
    tags=["healthcheck"],
)


@health_router.get("/", status_code=200)
async def check_health():
    return "server is up and running "
