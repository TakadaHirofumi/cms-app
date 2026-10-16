# HTTPリクエスト受付
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import Article
from schemas import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    ArticleStatusUpdate
)
import crud


app = FastAPI(
    title="CMS API",
    description="記事管理システム用REST API"
)

# SQLAlchemyモデルに基づくテーブル作成
Base.metadata.create_all(bind=engine)

# 記事一覧取得
@app.get(
    "/api/articles",
    response_model=list[ArticleResponse]
)
def get_articles(
    db: Session = Depends(get_db)
):
    return crud.get_articles(db)

# 記事IDによる取得
@app.get(
    "/api/articles/{article_id}",
    response_model=ArticleResponse
)
def get_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    article = crud.get_article_by_id(
        db,
        article_id
    )
    if article is None:
        raise HTTPException(
            status_code=404,
            detail="記事が見つかりません"
        )
    return article

# 記事新規作成
@app.post(
    "/api/articles",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED
)
def create_article(
    request: ArticleCreate,
    db: Session = Depends(get_db)
):
    return crud.create_article(
        db,
        request
    )

# 記事編集
@app.put(
    "/api/articles/{article_id}",
    response_model=ArticleResponse
)
def update_article(
    article_id: int,
    request: ArticleUpdate,
    db: Session = Depends(get_db)
):
    article = crud.get_article_by_id(
        db,
        article_id
    )
    if article is None:
        raise HTTPException(
            status_code=404,
            detail="記事が見つかりません"
        )
    return crud.update_article(
        db,
        article,
        request
    )

# ステータス変更
@app.patch(
    "/api/articles/{article_id}/status",
    response_model=ArticleResponse
)
def update_article_status(
    article_id: int,
    request: ArticleStatusUpdate,
    db: Session = Depends(get_db)
):
    article = crud.get_article_by_id(
        db,
        article_id
    )
    if article is None:
        raise HTTPException(
            status_code=404,
            detail="記事が見つかりません"
        )
    return crud.update_article_status(
        db,
        article,
        request.status
    )

# 記事削除
@app.delete(
    "/api/articles/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    article = crud.get_article_by_id(
        db,
        article_id
    )
    if article is None:
        raise HTTPException(
            status_code=404,
            detail="記事が見つかりません"
        )
    crud.delete_article(
        db,
        article
    )