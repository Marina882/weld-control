from database import engine, Base
from models import AnalysisResult, DefectDetail, User

def init_database():
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы")

if __name__ == "__main__":
    init_database()