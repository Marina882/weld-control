from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from utils import load_model, process_image, process_video
import traceback
import os
import tempfile

model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    try:
        model = load_model('model/weld_detector_single.pt')
        print("Модель успешно загружена")
    except Exception as e:
        print(f"Ошибка загрузки модели: {e}")
        raise e
    yield
    model = None

app = FastAPI(title="Weld Detection ML Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"service": "Weld Detection ML Service", "status": "running", "model_loaded": model is not None}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": model is not None}

@app.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    try:
        image_bytes = await file.read()
        result = process_image(model, image_bytes)
        return JSONResponse(content={"success": True, "filename": file.filename, "result": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/video")
async def analyze_video(video: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    try:
        # Сохраняем видео во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            content = await video.read()
            tmp_file.write(content)
            video_path = tmp_file.name
        
        print(f"Видео получено: {video_path}, размер: {len(content)} байт")
        
        # Обрабатываем видео
        result = process_video(model, video_path)
        
        # Удаляем временный файл
        os.unlink(video_path)
        
        return JSONResponse(content={"success": True, "filename": video.filename, "result": result})
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Ошибка: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)