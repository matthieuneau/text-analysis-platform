import uvicorn
from fastapi import FastAPI
from routes import router

app = FastAPI(
    title="Authentication Service",
    description="JWT + Database authentication for microservices architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router, tags=["Authentication"])


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,  # Remove in production
        log_level="info",
    )
