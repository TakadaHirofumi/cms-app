# 記事、カテゴリ、タグのCRUD（取得・登録・更新・削除）をSQLAlchemyのSessionで実行
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, literal
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session, selectinload
from models import Article, ArticleStatus, Category, Tag, Comment, Revision, User, UserRole, NotificationRead
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
    sort="updated_desc",
    public_only=False,
    editor_user_id=None
):
    stmt = select(Article).options(*ARTICLE_OPTIONS)

    # 未ログイン・VIEWERは公開記事のみ、EDITORは公開記事と自分の記事を取得
    # 現在の分の翌分開始より前を対象にし、秒・マイクロ秒を切り捨てた比較と同じ結果にする
    next_minute = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=1)
    public_condition = and_(
        Article.status == ArticleStatus.PUBLISHED,
        Article.published_at.is_not(None),
        Article.published_at < next_minute
    )
    if public_only:
        stmt = stmt.where(public_condition)
    elif editor_user_id is not None:
        stmt = stmt.where(or_(public_condition, Article.author_user_id == editor_user_id))

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
    request: ArticleCreate,
    author_user_id: int
):
    article = Article(
        title=request.title,
        slug=request.slug,
        author_user_id=author_user_id,
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
    # 更新前の内容をリビジョンとして保存（記事更新と同じトランザクション）
    save_revision(db, article)

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
    # ステータス変更前の内容も履歴として保存
    save_revision(db, article)

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
        name=request.name
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

# タグ追加ボタンからタグを即時登録する
# 同名タグは既存のレコードを返し、重複登録しない
# DBのunique制約は同時リクエストによる重複も防止する
def create_tag(db: Session, name: str):
    existing = db.scalar(select(Tag).where(Tag.name == name))
    if existing is not None:
        return existing
    tag = Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

# タグ削除（記事本体は残し、中間テーブルの関連付けのみ解除）
def delete_tag(
    db: Session,
    tag: Tag
):
    # article_tagの関連レコードはDBのON DELETE CASCADEで削除
    db.delete(tag)
    db.commit()

# コメント一覧を作成日時・IDの昇順で取得
def get_comments(db: Session, article_id: int):
    return db.scalars(
        select(Comment).where(Comment.article_id == article_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    ).all()

# 公開済み記事にコメントを登録
def create_comment(db: Session, article_id: int, request):
    comment = Comment(
        article_id=article_id,
        author_name=request.author_name,
        body=request.body
    )
    # コメントそのものを通知データとして利用するため、通知テーブルへの登録は不要
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

# 記事の更新前スナップショットを保存（呼び出し元でcommitする）
def save_revision(db: Session, article: Article):
    revision = Revision(
        article_id=article.id,
        title=article.title,
        body=article.body,
        status=article.status
    )
    db.add(revision)
    db.flush()
    return revision

# リビジョン一覧を新しい順に取得
def get_revisions(db: Session, article_id: int):
    return db.scalars(
        select(Revision).where(Revision.article_id == article_id)
        .order_by(Revision.created_at.desc(), Revision.id.desc())
    ).all()

# 指定した記事に属するリビジョンを取得
def get_revision(db: Session, article_id: int, revision_id: int):
    return db.scalar(
        select(Revision).where(
            Revision.id == revision_id,
            Revision.article_id == article_id
        )
    )

# 復元前の内容を保存してから記事を復元
def restore_revision(db: Session, article: Article, revision: Revision):
    save_revision(db, article)

    article.title = revision.title
    article.body = revision.body
    article.status = revision.status
    # リビジョンには公開日時がないため、復元時は現在の公開日時を維持する
    # 非公開状態への復元では公開日時を解除する
    if article.status != ArticleStatus.PUBLISHED:
        article.published_at = None
    article.updated_at = datetime.now()

    db.commit()
    return get_article_by_id(db, article.id)

# メールアドレスでユーザーを取得
def get_user_by_email(db: Session, email: str):
    return db.scalar(select(User).where(User.email == email))

# 新規ユーザーを閲覧者として登録
def create_user(db: Session, request, password_hash: str):
    user = User(email=request.email, password_hash=password_hash,
                display_name=request.display_name, role=UserRole.VIEWER)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# 管理者向けユーザー一覧・権限更新
def get_users(db: Session):
    return db.scalars(select(User).order_by(User.id)).all()

def update_user_role(db: Session, user: User, role: UserRole):
    user.role = role
    db.commit()
    db.refresh(user)
    return user

# 旧方式の一括既読日時とコメント単位の既読情報を共通判定する
def notification_read_condition(user):
    receipt = select(NotificationRead.comment_id).where(
        NotificationRead.user_id == user.id,
        NotificationRead.comment_id == Comment.id
    ).exists()
    if user.notification_checked_at is not None:
        return or_(receipt, Comment.created_at <= user.notification_checked_at)
    return receipt

# ユーザーが作成した記事に対するコメントを通知として取得
def get_notifications(db: Session, user_id: int):
    user = db.get(User, user_id)
    rows = db.execute(
        select(Comment, Article.title, notification_read_condition(user).label("is_read"))
        .join(Article, Comment.article_id == Article.id)
        .where(Article.author_user_id == user_id)
        .order_by(Comment.created_at.desc(), Comment.id.desc())
    ).all()
    return [
        {
            "id": comment.id,
            "comment_id": comment.id,
            "article_id": comment.article_id,
            "article_title": article_title,
            "author_name": comment.author_name,
            "body": comment.body,
            "is_read": bool(is_read),
            "created_at": comment.created_at
        }
        for comment, article_title, is_read in rows
    ]

# 未読コメント数を取得する
def get_unread_count(db: Session, user_id: int):
    user = db.get(User, user_id)
    stmt = (
        select(func.count(Comment.id))
        .join(Article, Comment.article_id == Article.id)
        .where(Article.author_user_id == user_id, ~notification_read_condition(user))
    )
    return db.scalar(stmt) or 0

# 対象コメントのみ既読にする（重複実行でも既読情報は1件だけ）
def mark_notifications_read(db: Session, user_id: int, article_id=None, comment_ids=None):
    user = db.get(User, user_id)
    stmt = select(literal(user_id), Comment.id).join(Article, Comment.article_id == Article.id).where(
        Article.author_user_id == user_id, ~notification_read_condition(user)
    )
    if article_id is not None:
        stmt = stmt.where(Comment.article_id == article_id, Comment.id.in_(comment_ids or []))
    command = insert(NotificationRead).from_select(["user_id", "comment_id"], stmt)
    db.execute(command.on_duplicate_key_update(comment_id=NotificationRead.comment_id))
    db.commit()
