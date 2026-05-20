import cv2
import numpy as np
from PIL import Image
import io
import base64
import torch
import os
from ultralytics import RTDETR

# Словарь для переименования классов
CLASS_NAMES = {
    'adj': 'Смежные дефекты (брызги/дуги)',
    'int': 'Дефекты целостности',
    'geo': 'Геометрические дефекты',
    'pro': 'Дефекты постобработки',
    'non': 'Неполные провары',
    'good': 'Шов без дефектов'
}

# Цвета для классов (BGR формат)
CLASS_COLORS = {
    'adj': (0, 165, 255),
    'int': (0, 0, 255),
    'geo': (255, 0, 0),
    'pro': (0, 255, 255),
    'non': (255, 0, 255),
    'good': (0, 255, 0)
}

class SingleWeldDetector:
    def __init__(self, model_int, model_rest, int_class_id, 
                 conf_int=0.45, conf_rest=0.60, iou_thresh=0.35):
        self._rtdetr_int = model_int
        self._rtdetr_rest = model_rest
        self.int_class_id = int_class_id
        self.conf_int = conf_int
        self.conf_rest = conf_rest
        self.iou_thresh = iou_thresh
        self.names = model_rest.names
        self.int_names = model_int.names

    def predict(self, source, **kwargs):
        conf_int = kwargs.get('conf_int', self.conf_int)
        conf_rest = kwargs.get('conf_rest', self.conf_rest)
        
        results_int = self._rtdetr_int.predict(source=source, conf=conf_int, iou=0.5, verbose=False)
        results_rest = self._rtdetr_rest.predict(source=source, conf=conf_rest, iou=0.45, verbose=False)
        
        for i, (r_int, r_rest) in enumerate(zip(results_int, results_rest)):
            all_boxes = []
            device = torch.device('cpu')
            
            if r_int.boxes is not None:
                device = r_int.boxes.xyxy.device
            elif r_rest.boxes is not None:
                device = r_rest.boxes.xyxy.device
            
            # Собираем боксы от multiclass
            multiclass_boxes = []
            if r_rest.boxes is not None:
                for box in r_rest.boxes:
                    multiclass_boxes.append({
                        'xyxy': box.xyxy[0].to(device),
                        'conf': float(box.conf),
                        'cls': int(box.cls)
                    })
            
            # Обрабатываем int
            int_candidates = []
            if r_int.boxes is not None:
                for int_box in r_int.boxes:
                    int_xyxy = int_box.xyxy[0].to(device)
                    int_conf = float(int_box.conf)
                    
                    best_overlap = None
                    best_iou = 0
                    
                    for mc_box in multiclass_boxes:
                        iou = self.compute_iou(
                            int_xyxy.cpu().tolist(),
                            mc_box['xyxy'].cpu().tolist()
                        )
                        if iou > best_iou:
                            best_iou = iou
                            best_overlap = mc_box
                    
                    accept_as_int = False
                    
                    if best_iou < 0.3:
                        if int_conf >= 0.53:
                            accept_as_int = True
                    elif best_overlap['cls'] == self.int_class_id:
                        accept_as_int = True
                        int_conf = (int_conf + best_overlap['conf']) / 2
                    elif best_overlap['cls'] != self.int_class_id:
                        mc_conf = best_overlap['conf']
                        if int_conf > mc_conf + 0.38:
                            accept_as_int = True
                        elif int_conf > 0.72 and int_conf > mc_conf:
                            accept_as_int = True
                    
                    if accept_as_int:
                        int_candidates.append({
                            'xyxy': int_xyxy,
                            'conf': int_conf,
                            'cls': self.int_class_id
                        })
            
            # Добавляем НЕ-int от multiclass
            for mc_box in multiclass_boxes:
                if mc_box['cls'] != self.int_class_id:
                    all_boxes.append(mc_box)
            
            all_boxes.extend(int_candidates)
            
            # NMS
            if len(all_boxes) > 0:
                boxes_tensor = torch.stack([b['xyxy'] for b in all_boxes]).to(device)
                scores_tensor = torch.tensor([b['conf'] for b in all_boxes], device=device)
                classes_tensor = torch.tensor([b['cls'] for b in all_boxes], device=device)
                
                from torchvision.ops import nms
                keep = nms(boxes_tensor, scores_tensor, self.iou_thresh)
                
                r_rest.boxes_data = {
                    'xyxy': boxes_tensor[keep].cpu(),
                    'conf': scores_tensor[keep].cpu(),
                    'cls': classes_tensor[keep].cpu()
                }
            else:
                r_rest.boxes_data = None
        
        return results_rest
    
    @staticmethod
    def compute_iou(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0
    
    @classmethod
    def load(cls, path, device='cpu'):
        state = torch.load(path, map_location=device, weights_only=False)
        
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as f:
            int_tmp = f.name
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as f:
            rest_tmp = f.name
        
        torch.save(state['model_int_state'], int_tmp)
        torch.save(state['model_rest_state'], rest_tmp)
        
        model_int = RTDETR(int_tmp)
        model_rest = RTDETR(rest_tmp)
        
        os.unlink(int_tmp)
        os.unlink(rest_tmp)
        
        detector = cls(
            model_int=model_int,
            model_rest=model_rest,
            int_class_id=state['int_class_id'],
            conf_int=state.get('conf_int', 0.45),
            conf_rest=state.get('conf_rest', 0.60),
            iou_thresh=state.get('iou_thresh', 0.35)
        )
        
        return detector

def load_model(model_path='model/weld_detector_single.pt'):
    """Загрузка модели"""
    print(f"Загрузка модели из {model_path}...")
    model = SingleWeldDetector.load(model_path)
    print("Модель успешно загружена")
    return model

def process_image(model, image_bytes):
    """Обработка изображения моделью"""
    try:
        from PIL import ImageDraw, ImageFont
        
        # Конвертируем байты в изображение
        image = Image.open(io.BytesIO(image_bytes))
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Сохраняем оригинальное изображение ДО разметки
        _, original_buffer = cv2.imencode('.jpg', image_cv)
        original_base64 = base64.b64encode(original_buffer).decode('utf-8')
        
        # Запускаем детекцию
        results = model.predict(image_cv)
        
        # Конвертируем в PIL для нормального отображения русского текста
        image_pil = Image.fromarray(cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(image_pil)
        
        # Пробуем загрузить шрифт с поддержкой кириллицы
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 16)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                font = ImageFont.load_default()
                font_small = ImageFont.load_default()
        
        # Собираем информацию о дефектах
        defects_info = []
        
        for result in results:
            boxes_data = getattr(result, 'boxes_data', None)
            if boxes_data is not None:
                for i in range(len(boxes_data['xyxy'])):
                    x1, y1, x2, y2 = boxes_data['xyxy'][i].tolist()
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    confidence = float(boxes_data['conf'][i])
                    cls_id = int(boxes_data['cls'][i])
                    
                    class_name = result.names[cls_id]
                    russian_name = CLASS_NAMES.get(class_name, class_name)
                    color = CLASS_COLORS.get(class_name, (255, 255, 255))
                    
                    color_rgb = (color[2], color[1], color[0])
                    
                    draw.rectangle([(x1, y1), (x2, y2)], outline=color_rgb, width=3)
                    
                    label = f"{russian_name} ({confidence:.2f})"
                    
                    bbox = draw.textbbox((0, 0), label, font=font_small)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    text_bg = [(x1, y1 - text_height - 10), (x1 + text_width + 10, y1)]
                    draw.rectangle(text_bg, fill=color_rgb)
                    
                    draw.text((x1 + 5, y1 - text_height - 5), label, fill=(255, 255, 255), font=font_small)
                    
                    defect_info = {
                        'class': class_name,
                        'class_name': russian_name,
                        'confidence': round(confidence, 3),
                        'bbox': {
                            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                            'width': x2 - x1, 'height': y2 - y1
                        },
                        'center': {
                            'x': (x1 + x2) // 2,
                            'y': (y1 + y2) // 2
                        }
                    }
                    defects_info.append(defect_info)
        
        # Конвертируем обратно в OpenCV формат
        annotated_image = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
        
        # Конвертируем аннотированное изображение в base64
        _, buffer = cv2.imencode('.jpg', annotated_image)
        annotated_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Статистика
        class_stats = {}
        for defect in defects_info:
            class_name = defect['class_name']
            if class_name not in class_stats:
                class_stats[class_name] = {'count': 0, 'total_confidence': 0}
            class_stats[class_name]['count'] += 1
            class_stats[class_name]['total_confidence'] += defect['confidence']
        
        for class_name in class_stats:
            class_stats[class_name]['avg_confidence'] = round(
                class_stats[class_name]['total_confidence'] / class_stats[class_name]['count'], 3
            )
        
        # Определяем общее качество шва
        if not defects_info:
            quality = 'Шов годен'
        else:
            has_good = any(d['class'] == 'good' for d in defects_info)
            has_non = any(d['class'] == 'non' for d in defects_info)
            has_int = any(d['class'] == 'int' for d in defects_info)
            
            if all(d['class'] == 'good' for d in defects_info):
                quality = 'Шов годен'
            elif has_good and len(defects_info) == 1:
                quality = 'Шов годен'
            elif has_non or has_int:
                quality = 'Шов бракованный и не подлежит исправлению'
            else:
                quality = 'Шов бракованный, необходимо исправить дефекты'
        
        return {
            'defects': defects_info,
            'total_defects': len(defects_info),
            'class_stats': class_stats,
            'quality': quality,
            'annotated_image': annotated_base64,
            'original_frame': original_base64,  # ← чистое изображение
            'image_size': {
                'width': annotated_image.shape[1],
                'height': annotated_image.shape[0]
            }
        }
    except Exception as e:
        print(f"Ошибка обработки: {e}")
        import traceback
        traceback.print_exc()
        raise

def is_frame_quality_good(frame, min_brightness=30, max_brightness=200, min_sharpness=50):
    """
    Проверка качества кадра
    
    Параметры:
    - min_brightness: минимальная средняя яркость (чтобы отсеять слишком тёмные кадры)
    - max_brightness: максимальная средняя яркость (чтобы отсеять пересвеченные кадры)
    - min_sharpness: минимальная резкость (чтобы отсеять размытые кадры)
    """
    if frame is None:
        return False
    
    # Конвертируем в оттенки серого для анализа
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Проверка яркости
    mean_brightness = np.mean(gray)
    if mean_brightness < min_brightness or mean_brightness > max_brightness:
        return False
    
    # Проверка резкости (вариация Лапласиана)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < min_sharpness:
        return False
    
    return True


def normalize_frame(frame):
    """
    Нормализация кадра: выравнивание гистограммы и улучшение контраста
    """
    # Конвертируем в LAB для обработки яркости
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Выравнивание гистограммы для канала яркости (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    
    # Объединяем обратно
    lab_eq = cv2.merge([l_eq, a, b])
    frame_eq = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)
    
    return frame_eq


def process_video(model, video_path, num_frames=4):
    """
    Обработка видео - извлечение и анализ ключевых кадров с фильтрацией по качеству
    """
    try:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            raise Exception("Видео не содержит кадров")
        
        candidate_indices = []
        if total_frames <= num_frames:
            candidate_indices = list(range(total_frames))
        else:
            step = total_frames // (num_frames + 1)
            candidate_indices = [step * (i + 1) for i in range(num_frames)]
        
        frames_results = []
        processed_count = 0
        
        for idx in candidate_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            if not is_frame_quality_good(frame):
                found_alternative = False
                for offset in [1, -1, 2, -2, 3, -3, 5, -5]:
                    alt_idx = idx + offset
                    if 0 <= alt_idx < total_frames:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, alt_idx)
                        ret_alt, alt_frame = cap.read()
                        if ret_alt and is_frame_quality_good(alt_frame):
                            frame = alt_frame
                            idx = alt_idx
                            found_alternative = True
                            break
                
                if not found_alternative:
                    continue
            
            frame = normalize_frame(frame)
            
            # Сохраняем исходный кадр ДО разметки
            _, original_buffer = cv2.imencode('.jpg', frame)
            original_frame_base64 = base64.b64encode(original_buffer).decode('utf-8')
            
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            result = process_image(model, frame_bytes)
            result['frame_index'] = idx
            result['frame_time'] = idx / cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0
            result['original_frame'] = original_frame_base64  # исходный кадр без разметки
            
            frames_results.append(result)
            processed_count += 1
            
            print(f"  Кадр {processed_count}: индекс {idx}, найдено дефектов: {result['total_defects']}")
        
        cap.release()
        
        # Находим подтверждённые дефекты (эталонный кадр + проверка на других)
        confirmed_defects, class_stats = get_confirmed_defects(frames_results)
        quality = get_quality_for_defects(confirmed_defects)
        
        # Создаём кадр с подтверждёнными дефектами на чистом изображении
        confirmed_frame = create_confirmed_frame(frames_results, confirmed_defects)
        
        final_result = {
            'frames': frames_results,
            'total_frames_analyzed': len(frames_results),
            'defects': confirmed_defects,
            'total_defects': len(confirmed_defects),
            'class_stats': class_stats,
            'quality': quality,
            'confirmed_frame': confirmed_frame
        }
        
        print(f"Проанализировано кадров: {len(frames_results)}, подтверждённых дефектов: {len(confirmed_defects)}")
        
        return final_result
    
    except Exception as e:
        print(f"Ошибка обработки видео: {e}")
        raise


def create_confirmed_frame(frames_results, confirmed_defects):
    """
    Создаёт кадр с отрисованными подтверждёнными дефектами на ЧИСТОМ изображении
    """
    if not frames_results or not confirmed_defects:
        return None
    
    # Находим эталонный кадр
    reference_frame = max(frames_results, key=lambda f: f.get('total_defects', 0))
    
    # Берём ИСХОДНОЕ изображение (без разметки)
    original_base64 = reference_frame.get('original_frame', reference_frame.get('annotated_image', ''))
    if not original_base64:
        return None
    
    image_data = base64.b64decode(original_base64)
    image_cv = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
    
    from PIL import ImageDraw, ImageFont
    
    image_pil = Image.fromarray(cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image_pil)
    
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 16)
    except:
        try:
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font_small = ImageFont.load_default()
    
    # Рисуем только подтверждённые дефекты
    for defect in confirmed_defects:
        x1 = defect['center']['x'] - defect['bbox']['width'] // 2
        y1 = defect['center']['y'] - defect['bbox']['height'] // 2
        x2 = defect['center']['x'] + defect['bbox']['width'] // 2
        y2 = defect['center']['y'] + defect['bbox']['height'] // 2
        
        class_name = defect['class']
        russian_name = CLASS_NAMES.get(class_name, class_name)
        color = CLASS_COLORS.get(class_name, (255, 255, 255))
        color_rgb = (color[2], color[1], color[0])
        
        # Рамка
        draw.rectangle([(x1, y1), (x2, y2)], outline=color_rgb, width=3)
        
        # Подпись
        label = f"{russian_name} ({defect['confidence']:.2f})"
        bbox = draw.textbbox((0, 0), label, font=font_small)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        draw.rectangle([(x1, y1 - text_height - 10), (x1 + text_width + 10, y1)], fill=color_rgb)
        draw.text((x1 + 5, y1 - text_height - 5), label, fill=(255, 255, 255), font=font_small)
    
    annotated_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode('.jpg', annotated_cv)
    confirmed_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return confirmed_base64


def get_confirmed_defects(frames_results):
    """
    Поиск подтверждённых дефектов.
    Берём кадр с наибольшим количеством дефектов как эталонный,
    оставляем только те дефекты, которые встречаются ещё хотя бы на одном другом кадре.
    """
    if not frames_results:
        return [], {}
    
    if len(frames_results) == 1:
        defects = frames_results[0].get('defects', [])
        class_stats = {}
        for d in defects:
            name = d['class_name']
            if name not in class_stats:
                class_stats[name] = {'count': 0, 'total_confidence': 0}
            class_stats[name]['count'] += 1
            class_stats[name]['total_confidence'] += d['confidence']
        for name in class_stats:
            if class_stats[name]['count'] > 0:
                class_stats[name]['avg_confidence'] = round(
                    class_stats[name]['total_confidence'] / class_stats[name]['count'], 3
                )
        return defects, class_stats
    
    # Находим эталонный кадр (с максимальным количеством дефектов)
    reference_frame = max(frames_results, key=lambda f: f.get('total_defects', 0))
    reference_defects = reference_frame.get('defects', [])
    
    if not reference_defects:
        return [], {}
    
    # Собираем дефекты с остальных кадров
    other_defects = []
    for frame in frames_results:
        if frame != reference_frame:
            for defect in frame.get('defects', []):
                other_defects.append(defect)
    
    # Проверяем каждый дефект эталонного кадра
    confirmed_defects = []
    
    for ref_defect in reference_defects:
        found_match = False
        
        for other_defect in other_defects:
            if ref_defect['class'] != other_defect['class']:
                continue
            
            dx = abs(ref_defect['center']['x'] - other_defect['center']['x'])
            dy = abs(ref_defect['center']['y'] - other_defect['center']['y'])
            
            if dx < 100 and dy < 100:
                found_match = True
                break
        
        if found_match:
            confirmed_defects.append(ref_defect)
    
    # Статистика
    class_stats = {}
    for d in confirmed_defects:
        name = d['class_name']
        if name not in class_stats:
            class_stats[name] = {'count': 0, 'total_confidence': 0}
        class_stats[name]['count'] += 1
        class_stats[name]['total_confidence'] += d['confidence']
    
    for name in class_stats:
        if class_stats[name]['count'] > 0:
            class_stats[name]['avg_confidence'] = round(
                class_stats[name]['total_confidence'] / class_stats[name]['count'], 3
            )
    
    return confirmed_defects, class_stats


def get_quality_for_defects(defects):
    """Определение качества по списку дефектов"""
    if not defects:
        return 'Шов годен'
    
    has_good = any(d['class'] == 'good' for d in defects)
    has_non = any(d['class'] == 'non' for d in defects)
    has_int = any(d['class'] == 'int' for d in defects)
    
    if all(d['class'] == 'good' for d in defects):
        return 'Шов годен'
    elif has_good and len(defects) == 1:
        return 'Шов годен'
    elif has_non or has_int:
        return 'Шов бракованный и не подлежит исправлению'
    else:
        return 'Шов бракованный, необходимо исправить дефекты'