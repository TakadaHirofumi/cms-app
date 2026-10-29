# DBテーブル定義
from datetime import datetime
from enum import Enum
from sqlalchemy import BigInteger, Column, DateTime, Enum as SQLEnum, ForeignKey, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


# 記事ステータス定義
class ArticleStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

# 記事とタグの中間テーブル（多対多の関連付け）
article_tag = Table(
    "article_tag",
    Base.metadata,
    Column("article_id", BigInteger, ForeignKey("article.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", BigInteger, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
)

# カテゴリテーブル定義
class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True
    )

    slug: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True
    )

    # 1カテゴリに複数の記事を紐付ける
    articles: Mapped[list["Article"]] = relationship(
        back_populates="category",
        passive_deletes=True
    )

# タグテーブル定義
class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True
    )

    # 記事とタグの多対多の関連付け
    articles: Mapped[list["Article"]] = relationship(
        secondary=article_tag,
        back_populates="tags",
        passive_deletes=True
    )

# 記事テーブル定義
class Article(Base):
    __tablename__ = "article"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    slug: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True
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

    # カテゴリへの外部キー（削除時はNULL）
    category_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("category.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # カテゴリ、タグを記事詳細のレスポンスで参照
    category: Mapped[Category | None] = relationship(
        back_populates="articles"
    )

    tags: Mapped[list[Tag]] = relationship(
        secondary=article_tag,
        back_populates="articles",
        passive_deletes=True
    )
