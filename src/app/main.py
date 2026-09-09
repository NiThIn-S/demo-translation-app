import asyncio
import uvicorn
# from logging.config import dictConfig # before fastapi

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.logger import get_logger

log = get_logger("main")

origins = ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Establishing lifespan events.
    """

    await asyncio.sleep(0.2)
    log.info("Application started.")

    yield

    log.warning("Application shutting down., ")


openapi_url = "/openapi.json"

app = FastAPI(
    # title=config.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
    openapi_url=openapi_url,
)


# CORS origin config.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", status_code=status.HTTP_200_OK)
async def healthcheck():
    return True


# Initializing all routers with prefix.
router_prefix = "/api/v1"

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        # port=config.BACKEND_PORT,
        host="0.0.0.0",
        workers=1,
        reload=not True,
        # use_colors=not False
    )
