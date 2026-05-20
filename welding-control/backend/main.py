from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import analysis, reports
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
import auth
import logging
import time
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - report-checker - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding='utf-8')
    ]
)
logger = logging.getLogger("report-checker")

app = FastAPI(title="Welding Quality Control API", version="1.0.0")

# Prometheus метрики (ПЕРЕД CORS и логированием)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Логирование запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(auth.router)
app.mount("/images", StaticFiles(directory="analysis_images"), name="images")

@app.get("/")
async def root():
    return {"service": "Welding Quality Control Backend", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)