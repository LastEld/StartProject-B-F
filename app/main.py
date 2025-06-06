
# app/main.py

# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from starlette.middleware.sessions import SessionMiddleware # TODO: Verify if SessionMiddleware is needed alongside JWT bearer token auth.
import os
import logging

# Импортируем роутеры (production way)
from app.api.ai_context import router as ai_context_router
from app.api.auth import router as auth_router
from app.api.devlog import router as devlog_router
from app.api.jarvis import router as jarvis_router
from app.api.plugin import router as plugin_router
from app.api.project import router as project_router
from app.api.settings import router as settings_router
from app.api.task import router as task_router
from app.api.team import router as team_router
from app.api.template import router as template_router
from app.api.user import router as user_router

from app.core.settings import settings
from app.core.exceptions import PluginNotFoundError, SpecificTemplateNotFoundError # Using SpecificTemplateNotFoundError
from fastapi import Request 
from fastapi.responses import JSONResponse 

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

# CORS origins
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Добавь production frontend
    "https://your-production-frontend.com",
]

app = FastAPI(
    title="DevOS Jarvis Web API",
    version="1.0.0",
    description="Production-ready modular AI project management backend",
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# TODO: Verify if SessionMiddleware is needed alongside JWT bearer token auth.
# app.add_middleware(
#     SessionMiddleware,
#     secret_key=settings.SECRET_KEY,
# )

# Роутеры
app.include_router(ai_context_router)
app.include_router(auth_router)
app.include_router(devlog_router)
app.include_router(jarvis_router)
app.include_router(plugin_router)
app.include_router(project_router)
app.include_router(settings_router)
app.include_router(task_router)
app.include_router(team_router)
app.include_router(template_router)
app.include_router(user_router)

# Health check & root
@app.get("/", tags=["Health"])
def root():
    return {"status": "DevOS Jarvis Web API is running!"}

@app.get("/health", tags=["Health"])
def health():
    return {"ok": True}

# Exception/Logging block (production best practices)
@app.on_event("startup")
async def startup_event():
    logger.info("Starting DevOS Jarvis Web API")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Stopping DevOS Jarvis Web API")

# Можно добавить кастомные exception handlers и advanced logging

@app.exception_handler(PluginNotFoundError)
async def plugin_not_found_exception_handler(request: Request, exc: PluginNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )

@app.exception_handler(SpecificTemplateNotFoundError) # Using SpecificTemplateNotFoundError
async def specific_template_not_found_exception_handler(request: Request, exc: SpecificTemplateNotFoundError): 
    return JSONResponse(
        status_code=exc.status_code if hasattr(exc, 'status_code') else 404, 
        content={"detail": exc.detail if hasattr(exc, 'detail') else str(exc)},
    )

# Old TemplateNotFound handler can be removed if it's confirmed SpecificTemplateNotFoundError is used everywhere

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=bool(os.getenv("DEBUG", False))
    )
