from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import secrets
import string

def generate_weld_id():
    today = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"WELD-{today}-{random_part}"

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    weld_id = Column(String(50), unique=True, default=generate_weld_id)
    analysis_date = Column(DateTime, default=datetime.now)
    analysis_type = Column(String(20))
    quality = Column(String(100))
    total_defects = Column(Integer)
    operator_name = Column(String(100), default="Петр")
    image_path = Column(String(500))
    original_image_path = Column(String(500))
    edited = Column(Boolean, default=False) 
    
    defects = relationship("DefectDetail", back_populates="result", cascade="all, delete-orphan")


class DefectDetail(Base):
    __tablename__ = "defect_details"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(Integer, ForeignKey("analysis_results.id"))
    class_name = Column(String(100))
    confidence = Column(Float)
    x_position = Column(Float)
    y_position = Column(Float)
    width = Column(Float)
    height = Column(Float)
    frame_index = Column(Integer, default=0)
    
    result = relationship("AnalysisResult", back_populates="defects")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(200))
    login = Column(String(50), unique=True)
    password = Column(String(200))