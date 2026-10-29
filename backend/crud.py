# 記事、カテゴリ、タグのCRUD（取得・登録・更新・削除）をSQLAlchemyのSessionで実行
from datetime import datetime
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session, selectinload
from models import Article, ArticleStatus, Category, Tag
from schemas import ArticleCreate, ArticleUpdate


# 記事取得時にカテゴリとタグをまとめて読み込む
ARTICLE_OPTIONS = (
    selectinload(Article.category),
    selectinload(Article.tags)
)

# 検索条件と並び替えを指定して記事一覧を取得
def get_articles(
    db: Session,
    *,
    status=None,
    category_id=None,
    tag_ids=None,
    keyword=None,
    sort="updated_desc"
):
    stmt = select(Article).options(*ARTICLE_OPTIONS)

    # ステータス・カテゴリ・タグの絞り込み
    if status is not None:
        stmt = stmt.where(Article.status == status)
    if category_id is not None:
        stmt = stmt.where(Article.category_id == category_id)
    if tag_ids:
        stmt = stmt.where(Article.tags.any(Tag.id.in_(tag_ids)))

    # タイトル・本文を大文字小文字を区別せず部分一致検索
    if keyword:
        pattern = f"%{keyword.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Article.title).like(pattern),
                func.lower(Article.body).like(pattern)
            )
        )

    # 更新日時降順・公開日時降順・タイトル昇順
    orders = {
        "updated_desc": (Article.updated_at.desc(), Article.id.desc()),
        "published_desc": (Article.published_at.desc(), Article.id.desc()),
        "title_asc": (Article.title.asc(), Article.id.asc())
    }

    return db.scalars(
        stmt.order_by(*orders[sort])
    ).all()

# 記事IDによる取得
def get_article_by_id(
    db: Session,
    article_id: int
):
    return db.scalar(
        select(Article)
        .options(*ARTICLE_OPTIONS)
        .where(Article.id == article_id)
    )

# カテゴリIDによる取得
def get_category(
    db: Session,
    category_id: int
):
    return db.get(Category, category_id)

# タグIDによる取得
def get_tag(
    db: Session,
    tag_id: int
):
    return db.get(Tag, tag_id)

# カテゴリ一覧をIDの昇順で取得
def get_categories(db: Session):
    return db.scalars(
        select(Category).order_by(Category.id)
    ).all()

# タグ一覧をIDの昇順で取得
def get_tags(db: Session):
    return db.scalars(
        select(Tag).order_by(Tag.id)
    ).all()

# 記事スラッグの重複チェック（編集時は自分の記事IDを除外）
def slug_exists(
    db: Session,
    slug: str,
    exclude_id=None
):
    stmt = select(Article.id).where(Article.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Article.id != exclude_id)
    return db.scalar(stmt.limit(1)) is not None

# 指定タグを取得し、未登録のタグがあれば新規登録する
def resolve_tags(
    db: Session,
    names: list[str]
):
    tags = []
    for name in names:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags

# 記事作成
def create_article(
    db: Session,
    request: ArticleCreate
):
    article = Article(
        title=request.title,
        slug=request.slug,
        body=request.body,
        status=request.status,
        category_id=request.category_id,
        published_at=(request.published_at or datetime.now())
        if request.status == ArticleStatus.PUBLISHED else None
    )

    # 記事とタグを関連付けて保存
    article.tags = resolve_tags(db, request.tag_names)
    db.add(article)
    db.commit()

    # 保存した記事をカテゴリ・タグ付きで再取得
    return get_article_by_id(db, article.id)

# 記事編集
def update_article(
    db: Session,
    article: Article,
    request: ArticleUpdate
):
    article.title = request.title
    article.slug = request.slug
    article.body = request.body
    article.category_id = request.category_id
    article.status = request.status
    article.published_at = (
        request.published_at or datetime.now()
    ) if request.status == ArticleStatus.PUBLISHED else None
    article.tags = resolve_tags(db, request.tag_names)
    article.updated_at = datetime.now()

    db.commit()

    return get_article_by_id(db, article.id)

# ステータス変更
def update_article_status(
    db: Session,
    article: Article,
    status: ArticleStatus
):
    # 新たに公開へ変更した場合は現在日時を設定
    # 既に公開中の場合は予約公開日時を維持する
    if status == ArticleStatus.PUBLISHED and article.status != ArticleStatus.PUBLISHED:
        article.published_at = datetime.now()
    elif status != ArticleStatus.PUBLISHED:
        article.published_at = None

    article.status = status
    article.updated_at = datetime.now()

    db.commit()

    return get_article_by_id(db, article.id)

# 記事削除
def delete_article(
    db: Session,
    article: Article
):
    db.delete(article)
    db.commit()

# カテゴリ作成
def create_category(
    db: Session,
    request
):
    category = Category(
        name=request.name,
        slug=request.slug
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return category

# カテゴリ削除（紐付く記事は削除せずカテゴリなしにする）
def delete_category(
    db: Session,
    category: Category
):
    # カテゴリ削除前に、関連する記事のcategory_idをNULLに更新
    db.query(Article).filter(
        Article.category_id == category.id
    ).update(
        {Article.category_id: None},
        synchronize_session=False
    )

    db.delete(category)
    db.commit()

# タグ削除（記事本体は残し、中間テーブルの関連付けのみ解除）
def delete_tag(
    db: Session,
    tag: Tag
):
    # article_tagの関連レコードはDBのON DELETE CASCADEで削除
    db.delete(tag)
    db.commit()
