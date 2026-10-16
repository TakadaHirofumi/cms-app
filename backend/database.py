# DB接続管理
import os

from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker, DeclarativeBase


# database.pyと同じフォルダにある.envを読み込む
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# .env(環境変数)からDB接続情報を取得
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

# MySQL接続URLを生成
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

# DBエンジン
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

# DBセッション
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# SQLAlchemyのベースクラス
class Base(DeclarativeBase):
    pass

# FastAPIからDBセッションを取得するための関数
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
