import sys
import uvicorn
from jarvis.config.settings import settings
from jarvis.observability.logging_config import logger


def main():
    logger.info(f"Starting J.A.R.V.I.S Core Service v4 on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "jarvis.gateway.server:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level="info" if settings.DEBUG else "warning",
        reload=False
    )


if __name__ == "__main__":
    main()
