from fastapi import FastAPI

from app.routes.order_routes import router as order_router
from app.routes.user_routes import router as user_router


app = FastAPI(
    title="LogistiAI Backend",
    version="0.1.0"
)


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


app.include_router(order_router)
app.include_router(user_router)