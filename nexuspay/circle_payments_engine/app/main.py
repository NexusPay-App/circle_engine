from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Circle Payments Engine",
    description="API for developer-controlled wallets and Circle integration",
    version="1.0.0"
)

app.include_router(router)
