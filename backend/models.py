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

# ユーザー権限定義
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

# ユーザーテーブル定義
class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        nullable=False,
        default=UserRole.VIEWER
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    
    # 通知画面を最後に確認した日時
    notification_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    # ユーザーが作成した記事
    articles: Mapped[list["Article"]] = relationship(back_populates="author")

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

    # 記事の作成者
    author_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False
    )

    author: Mapped[User] = relationship(back_populates="articles")

    # カテゴリ、タグを記事詳細のレスポンスで参照
    category: Mapped[Category | None] = relationship(
        back_populates="articles"
    )

    tags: Mapped[list[Tag]] = relationship(
        secondary=article_tag,
        back_populates="articles",
        passive_deletes=True
    )

    # 記事に紐付くコメントとリビジョン（削除時はDBのCASCADEを使用）
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="article",
        passive_deletes=True
    )

    revisions: Mapped[list["Revision"]] = relationship(
        back_populates="article",
        passive_deletes=True
    )

# コメントテーブル定義
class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    article_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("article.id", ondelete="CASCADE"),
        nullable=False
    )

    author_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    # コメントから記事を参照
    article: Mapped[Article] = relationship(
        back_populates="comments"
    )

# 記事の変更履歴テーブル定義
class Revision(Base):
    __tablename__ = "revision"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    article_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("article.id", ondelete="CASCADE"),
        nullable=False
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
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    # リビジョンから記事を参照
    article: Mapped[Article] = relationship(
        back_populates="revisions"
    )

# コメント単位の通知既読情報（通知本文は既存コメントから取得）
class NotificationRead(Base):
    __tablename__ = "notification_read"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True
        )
    
    comment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("comment.id", ondelete="CASCADE"),
        primary_key=True
    )
