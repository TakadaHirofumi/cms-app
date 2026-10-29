# APIの受付と制御
from datetime import datetime
from typing import Literal
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import ArticleStatus
from schemas import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    ArticleStatusUpdate,
    CategoryCreate,
    CategoryResponse,
    TagResponse
)
import crud


# FastAPIのインスタンスを作成し、タイトルと説明を設定
app = FastAPI(
    title="CMS API",
    description="記事管理システム用REST API"
)

# SQLAlchemyモデルに基づくテーブル作成
Base.metadata.create_all(bind=engine)

# DB更新時の一意制約違反・参照整合性違反をHTTP 409に変換
def persist(
    db: Session,
    operation
):
    try:
        return operation()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="重複データまたは参照整合性エラーです"
        )

# 記事のレスポンスを生成し、公開予約中かを判定
def article_response(article):
    # MySQL DATETIMEと同じタイムゾーンなしの日本時間で比較
    return ArticleResponse.model_validate(article).model_copy(
        update={
            "is_scheduled": (
                article.status == ArticleStatus.PUBLISHED
                and article.published_at is not None
                and article.published_at.replace(second=0, microsecond=0)
                > datetime.now().replace(second=0, microsecond=0)
            )
        }
    )

# 指定カテゴリの存在を確認（未指定の場合は許可）
def ensure_category(
    db: Session,
    category_id: int | None
):
    if category_id is not None and crud.get_category(db, category_id) is None:
        raise HTTPException(
            status_code=422,
            detail="指定されたカテゴリが存在しません"
        )

# 記事スラッグの重複を確認（編集時は自身を除外）
def ensure_slug(
    db: Session,
    slug: str,
    exclude_id=None
):
    if crud.slug_exists(db, slug, exclude_id):
        raise HTTPException(
            status_code=409,
            detail="このスラッグは既に使用されています"
        )

# GET /api/articles：検索条件・並び替えを指定して記事一覧を返却
@app.get(
    "/api/articles",
    response_model=list[ArticleResponse]
)
def get_articles(
    status: ArticleStatus | None = None,
    category_id: int | None = None,
    tag_ids: list[int] | None = Query(default=None),
    keyword: str | None = None,
    sort: Literal["updated_desc", "published_desc", "title_asc"] = "updated_desc",
    db: Session = Depends(get_db)
):
    articles = crud.get_articles(
        db,
        status=status,
        category_id=category_id,
        tag_ids=tag_ids,
        keyword=keyword,
        sort=sort
    )
    return [article_response(article) for article in articles]

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
    return article_response(article)

# POST /api/articles：入力データを検証し、記事を新規登録
@app.post(
    "/api/articles",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED
)
def create_article(
    request: ArticleCreate,
    db: Session = Depends(get_db)
):
    # カテゴリとスラッグの整合性を確認してから保存
    ensure_category(db, request.category_id)
    ensure_slug(db, request.slug)

    return article_response(
        persist(db, lambda: crud.create_article(db, request))
    )

# PUT /api/articles/{article_id}：指定記事のタイトル・本文・追加項目を更新
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

    ensure_category(db, request.category_id)
    ensure_slug(db, request.slug, article_id)

    return article_response(
        persist(db, lambda: crud.update_article(db, article, request))
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

    return article_response(
        persist(db, lambda: crud.update_article_status(db, article, request.status))
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

    persist(db, lambda: crud.delete_article(db, article))

# GET /api/categories：カテゴリ一覧を取得
@app.get(
    "/api/categories",
    response_model=list[CategoryResponse]
)
def get_categories(
    db: Session = Depends(get_db)
):
    return crud.get_categories(db)

# POST /api/categories：カテゴリを新規登録
@app.post(
    "/api/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED
)
def create_category(
    request: CategoryCreate,
    db: Session = Depends(get_db)
):
    return persist(db, lambda: crud.create_category(db, request))

# DELETE /api/categories/{category_id}：カテゴリを削除
@app.delete(
    "/api/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    category = crud.get_category(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=404,
            detail="カテゴリが見つかりません"
        )

    persist(db, lambda: crud.delete_category(db, category))

# GET /api/tags：タグ一覧を取得
@app.get(
    "/api/tags",
    response_model=list[TagResponse]
)
def get_tags(
    db: Session = Depends(get_db)
):
    return crud.get_tags(db)

# DELETE /api/tags/{tag_id}：タグを削除
@app.delete(
    "/api/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db)
):
    tag = crud.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(
            status_code=404,
            detail="タグが見つかりません"
        )

    persist(db, lambda: crud.delete_tag(db, tag))
