from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from database import get_db
from models import AnalysisResult
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import os
import glob
from datetime import datetime
import traceback
import base64
import io

router = APIRouter()

IMAGES_DIR = "analysis_images"

# Регистрируем шрифты с поддержкой кириллицы
FONT_NAME = 'Arial'
FONT_BOLD = 'Arial-Bold'

try:
    pdfmetrics.registerFont(TTFont('Arial', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'))
    FONT_NAME = 'Arial'
    FONT_BOLD = 'Arial-Bold'
    print("Шрифты Liberation зарегистрированы")
except Exception as e:
    print(f"Не удалось загрузить шрифты: {e}")
    FONT_NAME = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'


@router.post("/report/generate")
async def generate_report(report_data: dict):
    """
    Генерация отчёта по одному шву (PDF) - из текущих результатов
    """
    try:
        results = report_data.get('results', {})
        metadata = report_data.get('metadata', {})
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        is_video = 'frames' in results
        
        return await generate_pdf_report(results, metadata, timestamp, reports_dir, is_video)
            
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Ошибка генерации отчёта: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/weld/{weld_id}/pdf")
async def get_weld_report(weld_id: str, db: Session = Depends(get_db)):
    try:
        result = db.query(AnalysisResult).filter(AnalysisResult.weld_id == weld_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Шов не найден")
        
        defects = []
        class_stats = {}
        for d in result.defects:
            defects.append({
                'class': d.class_name,
                'class_name': d.class_name,
                'confidence': d.confidence,
                'center': {'x': d.x_position, 'y': d.y_position},
                'bbox': {'width': d.width, 'height': d.height},
                'frame_index': d.frame_index
            })
            name = d.class_name
            if name not in class_stats:
                class_stats[name] = {'count': 0, 'total_confidence': 0}
            class_stats[name]['count'] += 1
            class_stats[name]['total_confidence'] += d.confidence
        
        for name in class_stats:
            class_stats[name]['avg_confidence'] = round(class_stats[name]['total_confidence'] / class_stats[name]['count'], 3)
        
        results_data = {
            'total_defects': len(defects),
            'quality': result.quality,
            'class_stats': class_stats,
            'defects': defects,
            'edited': result.edited 
        }
        
        # Для видео — кадры
        if result.analysis_type == 'video':
            frames = []
            frame_pattern = os.path.join(IMAGES_DIR, f"{weld_id}_frame_*.jpg")
            for frame_file in sorted(glob.glob(frame_pattern))[:4]:
                if os.path.exists(frame_file):
                    with open(frame_file, 'rb') as f:
                        frames.append({'annotated_image': base64.b64encode(f.read()).decode('utf-8'), 'total_defects': 0})
            if frames:
                results_data['frames'] = frames
        
        if result.image_path and os.path.exists(result.image_path) and result.analysis_type != 'video':
            with open(result.image_path, 'rb') as f:
                results_data['annotated_image'] = base64.b64encode(f.read()).decode('utf-8')
        
        metadata = {'weldId': result.weld_id, 'operatorName': result.operator_name, 'edited': result.edited }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        return await generate_pdf_report(results_data, metadata, timestamp, reports_dir, result.analysis_type == 'video')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/daily")
async def get_daily_report(date: str, db: Session = Depends(get_db)):
    """
    Получение дневного отчёта
    """
    try:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        results = db.query(AnalysisResult).filter(
            func.date(AnalysisResult.analysis_date) == report_date
        ).order_by(AnalysisResult.analysis_date.asc()).all()
        
        good_count = sum(1 for r in results if 'годен' in r.quality.lower())
        defective_count = len(results) - good_count
        
        # Собираем операторов
        operators = {}
        for r in results:
            op_name = r.operator_name or "Неизвестный"
            if op_name not in operators:
                operators[op_name] = {'total': 0, 'good': 0, 'defective': 0}
            operators[op_name]['total'] += 1
            if 'годен' in r.quality.lower():
                operators[op_name]['good'] += 1
            else:
                operators[op_name]['defective'] += 1
        
        # Общая статистика дефектов
        defect_summary = {}
        seen_defects = set()
        
        welds = []
        for r in results:
            defect_details = {}
            for d in r.defects:
                key = f"{d.class_name}_{d.x_position}_{d.y_position}"
                if key not in seen_defects:
                    seen_defects.add(key)
                    if d.class_name not in defect_details:
                        defect_details[d.class_name] = 0
                    defect_details[d.class_name] += 1
                    
                    if d.class_name not in defect_summary:
                        defect_summary[d.class_name] = 0
                    defect_summary[d.class_name] += 1
            
            welds.append({
                "weld_id": r.weld_id,
                "analysis_type": r.analysis_type,
                "quality": r.quality,
                "total_defects": r.total_defects,
                "analysis_date": r.analysis_date.isoformat(),
                "operator_name": r.operator_name,
                "defect_details": defect_details,
                "edited": r.edited 
            })
        
        return {
            "date": date,
            "operators": operators,
            "total_welds": len(results),
            "good_welds": good_count,
            "defective_welds": defective_count,
            "defect_summary": defect_summary,
            "welds": welds
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/daily/download")
async def download_daily_report(date: str, format: str = "pdf", db: Session = Depends(get_db)):
    """
    Скачивание дневного отчёта (PDF)
    """
    try:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        results = db.query(AnalysisResult).filter(
            func.date(AnalysisResult.analysis_date) == report_date
        ).order_by(AnalysisResult.operator_name.asc(), AnalysisResult.analysis_date.asc()).all()
        
        filename = f"daily_report_{date}.pdf"
        filepath = os.path.join("reports", filename)
        
        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4
        
        # Заголовок
        c.setFont(FONT_BOLD, 18)
        c.drawString(50, height - 50, f"Отчет за {date}")
        
        # Линия
        c.setStrokeColor("#334340")
        c.setLineWidth(1)
        c.line(50, height - 60, width - 50, height - 60)
        
        y = height - 85
        
        # Собираем операторов
        operators = {}
        for r in results:
            op_name = r.operator_name or "Неизвестный"
            if op_name not in operators:
                operators[op_name] = {'total': 0, 'good': 0, 'defective': 0}
            operators[op_name]['total'] += 1
            if 'годен' in r.quality.lower():
                operators[op_name]['good'] += 1
            else:
                operators[op_name]['defective'] += 1
        
        good_count = sum(1 for r in results if 'годен' in r.quality.lower())
        defective_count = len(results) - good_count
        
        # Общая информация
        c.setFont(FONT_BOLD, 14)
        c.drawString(50, y, f"Всего швов: {len(results)}")
        y -= 25
        
        c.setFont(FONT_NAME, 12)
        c.setFillColor("#2e7d32")
        c.drawString(70, y, f"Годных: {good_count}")
        y -= 20
        
        c.setFillColor("#c62828")
        c.drawString(70, y, f"Бракованных: {defective_count}")
        y -= 25
        
        c.setFillColor("#000000")
        
        # Информация по операторам
        if operators:
            c.setFont(FONT_BOLD, 14)
            c.drawString(50, y, "Операторы:")
            y -= 22
            
            c.setFont(FONT_NAME, 11)
            for op_name, stats in operators.items():
                c.drawString(70, y, f"• {op_name}: всего {stats['total']} шв. (годных: {stats['good']}, брак: {stats['defective']})")
                y -= 18
            
            y -= 10
        
        # Общая статистика дефектов
        defect_summary = {}
        for r in results:
            seen_defects = set()
            for d in r.defects:
                key = f"{d.class_name}_{d.x_position}_{d.y_position}"
                if key not in seen_defects:
                    seen_defects.add(key)
                    if d.class_name not in defect_summary:
                        defect_summary[d.class_name] = 0
                    defect_summary[d.class_name] += 1
        
        if defect_summary:
            c.setFont(FONT_BOLD, 14)
            c.drawString(50, y, "Обнаруженные дефекты за день:")
            y -= 22
            
            c.setFont(FONT_NAME, 11)
            for class_name, count in defect_summary.items():
                text = f"  {class_name}: {count} шт."
                c.drawString(70, y, text)
                y -= 18
            
            y -= 10
        
        # Линия-разделитель
        c.setStrokeColor("#334340")
        c.line(50, y, width - 50, y)
        y -= 20
        
        # Информация по швам (сгруппированы по операторам)
        c.setFont(FONT_BOLD, 14)
        c.drawString(50, y, "Сварные швы:")
        y -= 25
        
        current_operator = None
        
        for r in results:
            # Если оператор сменился - пишем заголовок
            op_name = r.operator_name or "Неизвестный"
            if op_name != current_operator:
                current_operator = op_name
                
                if y < 80:
                    c.showPage()
                    y = height - 50
                
                c.setFont(FONT_BOLD, 13)
                c.setFillColor("#334340")
                c.drawString(50, y, f"Оператор: {op_name}")
                c.setFillColor("#000000")
                y -= 25
            
            # Собираем уникальные дефекты
            seen_defects = set()
            defect_details = {}
            for d in r.defects:
                key = f"{d.class_name}_{d.x_position}_{d.y_position}"
                if key not in seen_defects:
                    seen_defects.add(key)
                    if d.class_name not in defect_details:
                        defect_details[d.class_name] = 0
                    defect_details[d.class_name] += 1
            
            bg_height = 100
            if defect_details:
                bg_height += len(defect_details) * 16
            
            if y - bg_height < 50:
                c.showPage()
                y = height - 50
            
            # Фон
            c.setFillColor("#F9F4ED")
            c.rect(50, y - bg_height, width - 100, bg_height, fill=1, stroke=0)
            c.setFillColor("#000000")
            
            y -= 20
            c.setFont(FONT_BOLD, 13)
            c.drawString(70, y, f"Шов: {r.weld_id}")
            y -= 18
            
            c.setFont(FONT_NAME, 11)
            c.drawString(70, y, f"Тип: {'Видео' if r.analysis_type == 'video' else 'Изображение'}")
            y -= 18
            c.drawString(70, y, f"Качество: {r.quality}")
            y -= 18
            if r.edited:
                c.setFont(FONT_NAME, 10)
                c.setFillColor("#839958")
                c.drawString(70, y, "Результат отредактирован")
                c.setFillColor("#000000")
                y -= 18
            c.drawString(70, y, f"Дефектов: {r.total_defects}")
            y -= 18
            c.drawString(70, y, f"Время: {r.analysis_date.strftime('%H:%M:%S')}")
            y -= 20
            
            if defect_details:
                c.setFont(FONT_BOLD, 11)
                c.drawString(70, y, "Обнаруженные дефекты:")
                y -= 18
                
                c.setFont(FONT_NAME, 10)
                for class_name, count in defect_details.items():
                    c.drawString(90, y, f"• {class_name}: {count} шт.")
                    y -= 16
            
            y -= 15
        
        c.save()
        
        return FileResponse(filepath, media_type='application/pdf', filename=filename)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_pdf_report(results, metadata, timestamp, reports_dir, is_video):
    """Генерация PDF отчёта по одному шву"""
    
    filename = f"weld_report_{timestamp}.pdf"
    filepath = os.path.join(reports_dir, filename)
    
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # Заголовок с ID шва
    weld_id = metadata.get('weldId', '')
    title = f"Отчет контроля качества сварного шва {weld_id}" if weld_id else "Отчет контроля качества сварного шва"
    
    c.setFont(FONT_BOLD, 16)
    c.drawString(50, height - 50, title)
    
    # Линия
    c.setStrokeColor("#334340")
    c.setLineWidth(1)
    c.line(50, height - 60, width - 50, height - 60)
    
    y = height - 85
    
    # Дата и тип анализа
    c.setFont(FONT_NAME, 11)
    c.drawString(50, y, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    y -= 18
    c.drawString(50, y, f"Тип анализа: {'Видео' if is_video else 'Изображение'}")
    y -= 18
    
    # Оператор и комментарии
    if metadata:
        c.drawString(50, y, f"Оператор: {metadata.get('operatorName', 'Не указан')}")
        y -= 18
        # Пометка об редактировании
        if metadata.get('edited'):
            c.setFont(FONT_NAME, 10)
            c.setFillColor("#839958")
            c.drawString(50, y, "Результат отредактирован")
            c.setFillColor("#000000")
            y -= 18
        if metadata.get('comments'):
            c.drawString(50, y, f"Комментарии: {metadata.get('comments')}")
            y -= 18
    
    y -= 15
    
    try:
        if is_video:
            y = await draw_video_pdf(c, results, y, width, height)
        else:
            y = await draw_image_pdf(c, results, y, width, height)
    except Exception as e:
        print(f"Ошибка отрисовки PDF: {e}")
        c.setFont(FONT_NAME, 12)
        c.drawString(50, y, f"Ошибка при создании PDF: {str(e)}")
    
    c.save()
    
    return FileResponse(filepath, media_type='application/pdf', filename=filename)


async def draw_image_pdf(c, results, y, width, height):
    """Отрисовка результатов изображения"""
    
    # Изображение
    annotated_image = results.get('annotated_image', '')
    if annotated_image:
        try:
            image_data = base64.b64decode(annotated_image)
            img = ImageReader(io.BytesIO(image_data))
            
            img_width = 400
            img_height = 300
            
            if y - img_height < 50:
                c.showPage()
                y = height - 50
            
            c.drawImage(img, 50, y - img_height, width=img_width, height=img_height, preserveAspectRatio=True)
            y -= (img_height + 30)
        except Exception as e:
            print(f"Ошибка вставки изображения: {e}")
    
    # Результаты
    c.setFont(FONT_BOLD, 14)
    c.drawString(50, y, "Результаты анализа:")
    y -= 25
    
    c.setFont(FONT_NAME, 12)
    c.drawString(50, y, f"Всего дефектов: {results.get('total_defects', 0)}")
    y -= 20
    c.drawString(50, y, f"Качество шва: {results.get('quality', 'Не определено')}")
    y -= 25
    
    # Обнаруженные дефекты (статистика)
    class_stats = results.get('class_stats', {})
    if class_stats:
        c.setFont(FONT_BOLD, 12)
        c.drawString(50, y, "Обнаруженные дефекты:")
        y -= 22
        
        c.setFont(FONT_NAME, 11)
        for class_name, stats in class_stats.items():
            if y < 50:
                c.showPage()
                y = height - 50
            text = f"  {class_name}: {stats['count']} шт. (ср. уверенность: {stats['avg_confidence']*100:.1f}%)"
            c.drawString(70, y, text)
            y -= 18
    
    y -= 15
    
    # Детальная информация по каждому дефекту
    defects = results.get('defects', [])
    if defects:
        c.setFont(FONT_BOLD, 12)
        c.drawString(50, y, "Детальная информация:")
        y -= 22
        
        c.setFont(FONT_NAME, 10)
        for i, defect in enumerate(defects[:30]):
            if y < 50:
                c.showPage()
                y = height - 50
            
            text = f"  {i+1}. {defect['class_name']} | уверенность: {defect['confidence']*100:.1f}% | позиция: ({defect['center']['x']}, {defect['center']['y']}) | размер: {defect['bbox']['width']}x{defect['bbox']['height']}px"
            c.drawString(60, y, text)
            y -= 16
    
    return y


async def draw_video_pdf(c, results, y, width, height):
    """Отрисовка результатов видео"""
    
    frames = results.get('frames', [])
    
    # Статистика из ПОДТВЕРЖДЁННЫХ дефектов (class_stats уже готов)
    class_stats = results.get('class_stats', {})
    video_quality = results.get('quality', 'Не определено')
    
    # Все дефекты для детальной информации
    all_defects = results.get('defects', [])
    
    c.setFont(FONT_BOLD, 14)
    c.drawString(50, y, "Результаты анализа видео:")
    y -= 25
    
    c.setFont(FONT_NAME, 12)
    c.drawString(50, y, f"Всего дефектов: {results.get('total_defects', 0)}")
    y -= 20
    c.drawString(50, y, f"Качество шва: {video_quality}")
    y -= 25
    
    # Обнаруженные дефекты (статистика)
    if class_stats:
        c.setFont(FONT_BOLD, 12)
        c.drawString(50, y, "Обнаруженные дефекты:")
        y -= 22
        
        c.setFont(FONT_NAME, 11)
        for class_name, stats in class_stats.items():
            if y < 50:
                c.showPage()
                y = height - 50
            avg_conf = stats['avg_confidence'] if 'avg_confidence' in stats else (stats['total_confidence'] / stats['count'])
            text = f"  {class_name}: {stats['count']} шт. (ср. уверенность: {avg_conf*100:.1f}%)"
            c.drawString(70, y, text)
            y -= 18
    
    y -= 10
    
    # Детальная информация (все дефекты)
    if all_defects:
        c.setFont(FONT_BOLD, 12)
        c.drawString(50, y, "Детальная информация:")
        y -= 22
        
        c.setFont(FONT_NAME, 10)
        for i, defect in enumerate(all_defects[:30]):
            if y < 50:
                c.showPage()
                y = height - 50
            
            frame_info = f" (кадр {defect.get('frame_index', '?')})" if defect.get('frame_index') else ""
            text = f"  {i+1}. {defect['class_name']} | уверенность: {defect['confidence']*100:.1f}% | позиция: ({defect['center']['x']}, {defect['center']['y']}) | размер: {defect['bbox']['width']}x{defect['bbox']['height']}px{frame_info}"
            c.drawString(60, y, text)
            y -= 16
    
    y -= 20
    
    # Кадры
    for i, frame in enumerate(frames[:4]):
        if y < 250:
            c.showPage()
            y = height - 50
        
        c.setFont(FONT_BOLD, 11)
        c.drawString(50, y, f"Кадр {i + 1}")
        y -= 18
        
        annotated_image = frame.get('annotated_image', '')
        if annotated_image:
            try:
                image_data = base64.b64decode(annotated_image)
                img = ImageReader(io.BytesIO(image_data))
                img_width = 250
                img_height = 180
                c.drawImage(img, 50, y - img_height, width=img_width, height=img_height, preserveAspectRatio=True)
                y -= (img_height + 20)
            except:
                y -= 10
    
    return y


@router.get("/report/list")
async def list_reports():
    """Получение списка отчётов"""
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return {"reports": []}
    
    reports = []
    for filename in os.listdir(reports_dir):
        filepath = os.path.join(reports_dir, filename)
        reports.append({
            "filename": filename,
            "size": os.path.getsize(filepath),
            "created_at": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
        })
    
    return {"reports": sorted(reports, key=lambda x: x['created_at'], reverse=True)}