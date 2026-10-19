# APIの受付と制御
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


# FastAPIのインスタンスを作成し、タイトルと説明を設定
app = FastAPI(
    title="CMS API",
    description="記事管理システム用REST API"
)

# SQLAlchemyモデルに基づくテーブル作成
Base.metadata.create_all(bind=engine)

# GET /api/articles：作成日時の降順で記事一覧を返却
@app.get(
    "/api/articles",
    response_model=list[ArticleResponse]
)
def get_articles(
    db: Session = Depends(get_db)
):
    return crud.get_articles(db)

# GET /api/articles/{article_id}：指定IDの記事を返却、見つからない場合は404エラー
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

# POST /api/articles：入力データを検証し、下書き記事を新規登録
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

# PUT /api/articles/{article_id}：指定記事のタイトル、本文を更新
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

# PATCH /api/articles/{article_id}/status：ステータスと公開日時を更新
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

# DELETE /api/articles/{article_id}：指定記事を削除
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