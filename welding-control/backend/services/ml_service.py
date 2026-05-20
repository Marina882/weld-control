import httpx
from fastapi import UploadFile, HTTPException
import os
import cv2
import numpy as np

class MLService:
    def __init__(self):
        self.ml_service_url = os.getenv("ML_SERVICE_URL", "http://localhost:8001")
    
    async def check_health(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ml_service_url}/health")
                return response.json()
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}
    
    async def check_health(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ml_service_url}/health")
                return response.json()
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}
    
    async def analyze_image(self, file: UploadFile):
        try:
            file_content = await file.read()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"file": (file.filename, file_content, file.content_type)}
                response = await client.post(
                    f"{self.ml_service_url}/analyze/image",
                    files=files
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="ML-сервис недоступен")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def convert_video_to_mp4(self, input_path):
        """Конвертация видео в MP4 формат"""
        try:
            output_path = input_path.rsplit('.', 1)[0] + '_converted.mp4'
            print(f"Конвертирую {input_path} -> {output_path}")
        
            cap = cv2.VideoCapture(input_path)
        
            if not cap.isOpened():
                raise Exception("Не удалось открыть видео")
        
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0 or fps > 60:
                fps = 25.0
        
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
            if width <= 0 or height <= 0:
                width, height = 640, 480
        
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                frame_count += 1
        
            cap.release()
            out.release()
        
            print(f"Конвертировано кадров: {frame_count}")
        
            if frame_count > 0:
                return output_path
            else:
                raise Exception("Нет кадров в видео")
            
        except Exception as e:
            print(f"Ошибка конвертации: {e}")
            raise
    
    async def analyze_video(self, video_path: str):
        try:
            print(f"Анализ видео: {video_path}")

            if not video_path.endswith('.mp4'):
                video_path = self.convert_video_to_mp4(video_path)
            
            print(f"Отправляю {video_path} в ML-сервис...")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(video_path, 'rb') as f:
                    files = {"video": (os.path.basename(video_path), f, "video/mp4")}
                    response = await client.post(
                        f"{self.ml_service_url}/analyze/video",
                        files=files
                    )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
                    
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="ML-сервис недоступен")
        except Exception as e:
            print(f"Ошибка analyze_video: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analyze_frame(self, frame_data: dict):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.ml_service_url}/analyze/frame",
                    json=frame_data
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(status_code=response.status_code, detail="Ошибка ML-сервиса")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="ML-сервис недоступен")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))