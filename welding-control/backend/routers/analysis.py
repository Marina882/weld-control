from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from services.ml_service import MLService
from database import get_db
from models import AnalysisResult, DefectDetail
from sqlalchemy.orm import Session
import traceback
import os
import shutil
import base64
from datetime import datetime

router = APIRouter()
ml_service = MLService()

# Папка для хранения изображений
IMAGES_DIR = "analysis_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

def save_base64_image(base64_string, weld_id, frame_index=None):
    """Сохранение base64 изображения в файл"""
    try:
        if not base64_string:
            return None
        
        img_data = base64.b64decode(base64_string)
        
        if frame_index is not None:
            filename = f"{weld_id}_frame_{frame_index}.jpg"
        else:
            filename = f"{weld_id}.jpg"
        
        filepath = os.path.join(IMAGES_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(img_data)
        
        return filepath
    except Exception as e:
        print(f"Ошибка сохранения изображения: {e}")
        return None


@router.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    """
    Анализ загруженного изображения через ML-сервис
    БЕЗ сохранения в БД
    """
    try:
        result = await ml_service.analyze_image(file)
        return JSONResponse(content=result)
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Ошибка: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/video")
async def analyze_video(video: UploadFile = File(...)):
    """
    Анализ видео через ML-сервис
    БЕЗ сохранения в БД
    """
    try:
        temp_dir = "temp_videos"
        os.makedirs(temp_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = os.path.join(temp_dir, f"{timestamp}_{video.filename}")
        
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
        
        result = await ml_service.analyze_video(video_path)
        
        try:
            os.remove(video_path)
        except:
            pass
        
        return JSONResponse(content=result)
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Ошибка: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-results")
async def save_edited_results(data: dict, db: Session = Depends(get_db)):
    """
    Сохранение отредактированных результатов изображения в БД
    """
    try:
        db_result = AnalysisResult(
            analysis_type='image',
            quality=data.get('quality', 'Не определено'),
            total_defects=data.get('total_defects', 0),
            operator_name=data.get('operator_name', 'Оператор не определён'),
            edited=data.get('edited', False)  
        )

        db.add(db_result)
        db.flush()

        # Сохраняем чистое изображение (если есть original_frame)
        if data.get('original_frame'):
            original_path = save_base64_image(
                data['original_frame'],
                db_result.weld_id + '_original'
            )
            if original_path:
                db_result.original_image_path = original_path
        
        # Сохраняем размеченное изображение
        if data.get('annotated_image'):
            image_path = save_base64_image(
                data['annotated_image'],
                db_result.weld_id
            )
            if image_path:
                db_result.image_path = image_path
        
        # Сохраняем дефекты
        for defect in data.get('defects', []):
            db_defect = DefectDetail(
                result_id=db_result.id,
                class_name=defect['class_name'],
                confidence=defect['confidence'],
                x_position=defect['center']['x'],
                y_position=defect['center']['y'],
                width=defect['bbox']['width'],
                height=defect['bbox']['height']
            )
            db.add(db_defect)
        
        db.commit()
        print(f"Результат сохранен после редактирования, weld_id: {db_result.weld_id}")
        
        return {"success": True, "weld_id": db_result.weld_id}
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Ошибка: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-video-results")
async def save_edited_video_results(data: dict, db: Session = Depends(get_db)):
    try:
        frames = data.get('frames', [])
        unique_defects = data.get('defects', [])
        total_defects = data.get('total_defects', len(unique_defects))
        quality = data.get('quality', 'Не определено')
        
        db_result = AnalysisResult(
            analysis_type='video',
            quality=quality,
            total_defects=total_defects,
            operator_name=data.get('operator_name', 'Оператор не определён'),
            edited=data.get('edited', False)  
        )
        db.add(db_result)
        db.flush()
        
        # Сохраняем кадры
        for frame_idx, frame in enumerate(frames):
            if frame.get('annotated_image'):
                image_path = save_base64_image(frame['annotated_image'], db_result.weld_id, frame_idx + 1)
                if image_path and frame_idx == 0:
                    db_result.image_path = image_path
            # Сохраняем чистый первый кадр
            if frame.get('original_frame') and frame_idx == 0:
                original_path = save_base64_image(frame['original_frame'], db_result.weld_id + '_original')
                if original_path:
                    db_result.original_image_path = original_path

        # Сохраняем только подтверждённые дефекты
        for defect in unique_defects:
            db_defect = DefectDetail(
                result_id=db_result.id,
                class_name=defect['class_name'],
                confidence=defect['confidence'],
                x_position=defect['center']['x'],
                y_position=defect['center']['y'],
                width=defect['bbox']['width'],
                height=defect['bbox']['height'],
                frame_index=defect.get('frame_index', 0)
            )
            db.add(db_defect)
        
        db.commit()
        print(f"Видео сохранено: дефектов={total_defects}, weld_id={db_result.weld_id}")
        
        return {"success": True, "weld_id": db_result.weld_id}
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Ошибка: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/history")
async def get_analysis_history(limit: int = 50, db: Session = Depends(get_db)):
    """
    Получение истории анализов
    """
    try:
        results = db.query(AnalysisResult).order_by(
            AnalysisResult.analysis_date.desc()
        ).limit(limit).all()
        
        history = []
        for r in results:
            history.append({
                "id": r.id,
                "weld_id": r.weld_id,
                "analysis_date": r.analysis_date.isoformat(),
                "analysis_type": r.analysis_type,
                "quality": r.quality,
                "total_defects": r.total_defects,
                "operator_name": r.operator_name
            })
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{weld_id}")
async def get_analysis_detail(weld_id: str, db: Session = Depends(get_db)):
    """
    Получение детальной информации об анализе
    """
    try:
        result = db.query(AnalysisResult).filter(
            AnalysisResult.weld_id == weld_id
        ).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Анализ не найден")
        
        defects = []
        for d in result.defects:
            defects.append({
                "id": d.id,
                "class_name": d.class_name,
                "confidence": d.confidence,
                "x_position": d.x_position,
                "y_position": d.y_position,
                "width": d.width,
                "height": d.height,
                "frame_index": d.frame_index
            })
        
        return {
            "weld_id": result.weld_id,
            "analysis_date": result.analysis_date.isoformat(),
            "analysis_type": result.analysis_type,
            "quality": result.quality,
            "total_defects": result.total_defects,
            "operator_name": result.operator_name,
            "defects": defects
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/image/{weld_id}")
async def get_analysis_image(weld_id: str, db: Session = Depends(get_db)):
    """
    Получение сохраненного изображения анализа
    """
    try:
        result = db.query(AnalysisResult).filter(
            AnalysisResult.weld_id == weld_id
        ).first()
        
        if not result or not result.image_path:
            raise HTTPException(status_code=404, detail="Изображение не найдено")
        
        if not os.path.exists(result.image_path):
            raise HTTPException(status_code=404, detail="Файл изображения не найден")
        
        return FileResponse(result.image_path, media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))