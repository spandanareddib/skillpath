from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import models  # noqa: F401  (registers tables)
from .database import Base, engine
from .routers import auth, jobs, resumes


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SkillPath API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}
