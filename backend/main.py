from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database, models, seed, mq
from routers import auth, users, roles, students, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        seed.seed(db)
    finally:
        db.close()
    # 启动 Kafka 消费者与采样线程（Kafka/Redis 未启动时自动降级）
    mq.start()
    yield
    mq.stop()


app = FastAPI(title="SmartLearn API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(students.router)
app.include_router(stats.router)


@app.get("/")
def root():
    return {"message": "SmartLearn API", "docs": "/docs"}
