# DBテーブルに関する定義
from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


# 記事ステータス定義
class ArticleStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

# 記事テーブル定義
class Article(Base):
    __tablename__ = "article"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[ArticleStatus] = mapped_column(
        SQLEnum(ArticleStatus),
        nullable=False,
        default=ArticleStatus.DRAFT
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now
    )