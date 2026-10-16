# データベース操作
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from models import Article, ArticleStatus
from schemas import ArticleCreate, ArticleUpdate


# 記事一覧取得
def get_articles(db: Session):
    return db.scalars(
        select(Article)
        .order_by(
            Article.created_at.desc(),
            Article.id.desc()
        )
    ).all()

# 記事IDによる取得
def get_article_by_id(
    db: Session,
    article_id: int
):
    return db.get(Article, article_id)

# 記事新規作成
def create_article(
    db: Session,
    request: ArticleCreate
):
    article = Article(
        title=request.title,
        body=request.body,
        status=ArticleStatus.DRAFT,
        published_at=None
    )

    db.add(article)
    db.commit()
    db.refresh(article)

    return article

# 記事編集
def update_article(
    db: Session,
    article: Article,
    request: ArticleUpdate
):
    article.title = request.title
    article.body = request.body
    article.updated_at = datetime.now()

    db.commit()
    db.refresh(article)

    return article

# ステータス変更
def update_article_status(
    db: Session,
    article: Article,
    status: ArticleStatus
):
    article.status = status

    if status == ArticleStatus.PUBLISHED:
        article.published_at = datetime.now()
    else:
        article.published_at = None

    article.updated_at = datetime.now()

    db.commit()
    db.refresh(article)

    return article

# 記事削除
def delete_article(
    db: Session,
    article: Article
):
    db.delete(article)
    db.commit()