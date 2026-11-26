# APIの受付と制御
import crud
import os

from datetime import datetime
from typing import Literal
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import ArticleStatus, UserRole, User
from schemas import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    ArticleStatusUpdate,
    CategoryCreate,
    CategoryResponse,
    TagResponse,
    TagCreate,
    CommentCreate,
    CommentResponse,
    RevisionResponse,
    UserRegister, UserLogin, UserResponse, UserRoleUpdate, TokenResponse,
    NotificationResponse, UnreadCountResponse, NotificationReadRequest
)
from auth import (
    hash_password, verify_password, create_access_token,
    get_optional_user, get_current_user, require_editor, require_admin,
    ensure_article_owner
)
from fastapi.middleware.cors import CORSMiddleware


# FastAPIのインスタンスを作成し、タイトルと説明を設定
app = FastAPI(
    title="CMS API",
    description="記事管理システム用REST API"
)

# 許可したフロントエンドからのアクセスのみ受け付ける
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"]
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

# 公開済み・公開日時到達済みの記事のみ一般公開
def is_public_article(article):
    return (article.status == ArticleStatus.PUBLISHED
            and article.published_at is not None
            and article.published_at.replace(second=0, microsecond=0)
            <= datetime.now().replace(second=0, microsecond=0))

# 公開記事は全員、非公開記事はADMINまたは作成者本人のEDITORのみ閲覧可能
def can_view_article(article, user):
    return (is_public_article(article)
            or (user is not None and (
                user.role == UserRole.ADMIN
                or (user.role == UserRole.EDITOR and article.author_user_id == user.id)
            )))

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
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    articles = crud.get_articles(
        db,
        status=status,
        category_id=category_id,
        tag_ids=tag_ids,
        keyword=keyword,
        sort=sort,
        public_only=current_user is None or current_user.role == UserRole.VIEWER,
        editor_user_id=current_user.id if current_user is not None and current_user.role == UserRole.EDITOR else None
    )
    return [article_response(article) for article in articles]

# GET /api/articles/{article_id}：指定IDの記事を返却、見つからない場合は404エラー
@app.get(
    "/api/articles/{article_id}",
    response_model=ArticleResponse
)
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
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
    # 権限と記事作成者に応じて非公開記事の閲覧を拒否
    if not can_view_article(article, current_user):
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    return article_response(article)

# POST /api/articles：入力データを検証し、記事を新規登録
@app.post(
    "/api/articles",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED
)
def create_article(
    request: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    # カテゴリとスラッグの整合性を確認してから保存
    ensure_category(db, request.category_id)
    ensure_slug(db, request.slug)

    return article_response(
        persist(db, lambda: crud.create_article(db, request, current_user.id))
    )

# PUT /api/articles/{article_id}：指定記事のタイトル・本文・追加項目を更新
@app.put(
    "/api/articles/{article_id}",
    response_model=ArticleResponse
)
def update_article(
    article_id: int,
    request: ArticleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
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

    ensure_article_owner(current_user, article)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
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

    ensure_article_owner(current_user, article)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
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

    ensure_article_owner(current_user, article)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    return persist(db, lambda: crud.create_category(db, request))

# DELETE /api/categories/{category_id}：カテゴリを削除
@app.delete(
    "/api/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
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

# POST /api/tags：タグ追加ボタン押下時にタグを即時登録
@app.post(
    "/api/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED
)
def create_tag(
    request: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    # 同名タグが既にあればそのタグを返却
    return persist(db, lambda: crud.create_tag(db, request.name))

# DELETE /api/tags/{tag_id}：タグを削除
@app.delete(
    "/api/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    tag = crud.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(
            status_code=404,
            detail="タグが見つかりません"
        )

    persist(db, lambda: crud.delete_tag(db, tag))

# GET /api/articles/{article_id}/comments：記事のコメント一覧を取得
@app.get(
    "/api/articles/{article_id}/comments",
    response_model=list[CommentResponse]
)
def get_comments(article_id: int, db: Session = Depends(get_db),
                 current_user: User | None = Depends(get_optional_user)):
    # 対象記事が存在しない場合は404
    article = crud.get_article_by_id(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    # 記事詳細取得時と同じ閲覧権限でコメント一覧の取得を制限
    if not can_view_article(article, current_user):
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    return crud.get_comments(db, article_id)

# POST /api/articles/{article_id}/comments：公開済み記事にコメントを投稿
@app.post(
    "/api/articles/{article_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_comment(
    article_id: int,
    request: CommentCreate,
    db: Session = Depends(get_db)
):
    # 存在確認とステータス判定をバックエンドで実施
    article = crud.get_article_by_id(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    # 記事詳細取得時と同じ公開日時判定を使用
    if not is_public_article(article):
        raise HTTPException(status_code=403, detail="公開済みかつ公開日時を迎えた記事にのみコメントできます")
    return persist(db, lambda: crud.create_comment(db, article_id, request))

# GET /api/articles/{article_id}/revisions：変更履歴一覧を取得
@app.get(
    "/api/articles/{article_id}/revisions",
    response_model=list[RevisionResponse]
)
def get_revisions(article_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(require_editor)):
    article = crud.get_article_by_id(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    ensure_article_owner(current_user, article)
    return crud.get_revisions(db, article_id)

# POST /api/articles/{article_id}/revisions/{revision_id}/restore：過去の内容に復元
@app.post(
    "/api/articles/{article_id}/revisions/{revision_id}/restore",
    response_model=ArticleResponse
)
def restore_revision(
    article_id: int,
    revision_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    # 対象記事・対象リビジョンの存在と所属関係を確認
    article = crud.get_article_by_id(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    ensure_article_owner(current_user, article)
    revision = crud.get_revision(db, article_id, revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="リビジョンが見つかりません")
    return article_response(
        persist(db, lambda: crud.restore_revision(db, article, revision))
    )

# POST /api/auth/register：メールアドレスの重複を確認してユーザー登録
@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: UserRegister, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, request.email) is not None:
        raise HTTPException(status_code=409, detail="このメールアドレスは既に登録されています")
    return persist(db, lambda: crud.create_user(db, request, hash_password(request.password)))

# POST /api/auth/login：パスワードを検証してJWTを発行
@app.post("/api/auth/login", response_model=TokenResponse)
def login(request: UserLogin, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, request.email.strip().lower())
    # メールアドレスとパスワードの認証エラーを共通のメッセージで返す
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")
    return TokenResponse(access_token=create_access_token(user.id))

# GET /api/auth/me：ログイン中のユーザー情報を返す
# ログアウトはReact側でJWTを破棄する
@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# GET /api/users：ADMINのみユーザー一覧を取得
@app.get("/api/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return crud.get_users(db)

# PATCH /api/users/{user_id}/role：ADMINのみ権限変更
@app.patch("/api/users/{user_id}/role", response_model=UserResponse)
def update_user_role(user_id: int, request: UserRoleUpdate,
                     db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    # 管理者が自分自身を降格して管理者不在になることを防止
    if user.id == current_user.id and request.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="自分自身の管理者権限は変更できません")
    return persist(db, lambda: crud.update_user_role(db, user, request.role))

# GET /api/notifications：自分宛のコメント通知一覧
@app.get("/api/notifications", response_model=list[NotificationResponse])
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.get_notifications(db, current_user.id)

# GET /api/notifications/unread-count：未読通知件数を取得
@app.get("/api/notifications/unread-count", response_model=UnreadCountResponse)
def get_unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return UnreadCountResponse(unread_count=crud.get_unread_count(db, current_user.id))

# PATCH /api/notifications/read-all：自分の通知をまとめて既読にする
# コメント単位の既読情報をDBに保存する
@app.patch("/api/notifications/read-all", response_model=UnreadCountResponse)
def mark_notifications_read(db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    crud.mark_notifications_read(db, current_user.id)
    return UnreadCountResponse(unread_count=crud.get_unread_count(db, current_user.id))

# PATCH /api/notifications/articles/{article_id}/read：表示した記事のコメントのみ既読にする
@app.patch("/api/notifications/articles/{article_id}/read", response_model=UnreadCountResponse)
def mark_article_notifications_read(article_id: int, request: NotificationReadRequest,
                                    db: Session = Depends(get_db), current_user: User = Depends(require_editor)):
    article = crud.get_article_by_id(db, article_id)
    if article is None or article.author_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="記事が見つかりません")
    persist(db, lambda: crud.mark_notifications_read(db, current_user.id, article_id, request.comment_ids))
    return UnreadCountResponse(unread_count=crud.get_unread_count(db, current_user.id))
