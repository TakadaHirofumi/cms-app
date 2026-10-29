# CMSアプリのテストコード（フェーズ2版）
import os
import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from database import SessionLocal, engine
from main import app
from models import Article, Category, Tag


# テストクライアントを作成
@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

# テスト用記事の作成と削除を行う関数
@pytest.fixture
def make_article(client):
    created_ids = []
    created_tag_ids = set()

    # テスト用記事の作成
    def create(**kwargs):
        data = {
            "title": f"pytest-{uuid.uuid4().hex}",
            "slug": f"pytest-{uuid.uuid4().hex}",
            "body": "テスト本文",
            "tag_names": [],
        }
        data.update(kwargs)
        with SessionLocal() as db:
            existing_tag_ids = set(db.scalars(select(Tag.id)).all())

        response = client.post(
            "/api/articles",
            json=data,
        )
        assert response.status_code == 201, response.text
        article_id = response.json()["id"]
        created_ids.append(article_id)
        created_tag_ids.update(
            tag["id"] for tag in response.json()["tags"]
            if tag["id"] not in existing_tag_ids
        )
        return article_id

    # テストケースの関数に記事作成処理を渡す
    yield create

    # テスト終了後に記事を削除
    with SessionLocal() as db:
        for article_id in created_ids:
            article = db.get(Article, article_id)
            if article is not None:
                db.delete(article)
        db.commit()

        # 今回のテストで自動作成されたタグだけを削除
        for tag_id in created_tag_ids:
            tag = db.get(Tag, tag_id)
            if tag is not None:
                db.delete(tag)
        db.commit()

# DBから記事を取得
def get_db_article(article_id):
    with SessionLocal() as db:
        return db.get(Article, article_id)

# 記事作成後のAPIレスポンスも取得する共通処理
@pytest.fixture
def create_article(client, make_article):
    def create(**kwargs):
        article_id = make_article(**kwargs)
        response = client.get(f"/api/articles/{article_id}")
        assert response.status_code == 200, response.text
        return response.json()
    return create

# カテゴリと自動生成タグの後片付け
@pytest.fixture
def create_category(client):
    created_ids = []
    def create(unique, suffix=""):
        response = client.post(
            "/api/categories",
            json={"name": "カテゴリ" + unique + suffix, "slug": "cat-" + unique + suffix},
        )
        assert response.status_code == 201, response.text
        category = response.json()
        created_ids.append(category["id"])
        return category
    yield create

    with SessionLocal() as db:
        for category_id in created_ids:
            category = db.get(Category, category_id)
            if category is not None:
                db.delete(category)
        db.commit()

# テストごとに一意の名称を使用
@pytest.fixture
def unique():
    return uuid.uuid4().hex[:12]

# 一覧取得APIの検索結果から記事IDを取り出す
def search_ids(client, **params):
    response = client.get("/api/articles", params=params)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()]

# テストケース1：予約中判定と未来・過去・下書き・公開状態の変更の確認
# 期待値：未来の公開日時はTrue、過去の公開日時はFalse、下書きはFalse、ステータス変更後はFalseになること。
def test_scheduled_filter_sort(client, create_article, unique):
    future_time = (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds")
    past_time = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds")
    future = create_article(title="ZZ予約" + unique, status="PUBLISHED", published_at=future_time)
    past = create_article(title="AA公開" + unique, status="PUBLISHED", published_at=past_time)
    draft = create_article(title="下書き" + unique, status="DRAFT")
    assert client.get(f"/api/articles/{future['id']}").json()["is_scheduled"] is True
    assert client.get(f"/api/articles/{past['id']}").json()["is_scheduled"] is False
    assert client.get(f"/api/articles/{draft['id']}").json()["is_scheduled"] is False
    assert future["id"] in search_ids(client, status="PUBLISHED", keyword="予約" + unique, sort="title_asc")
    assert past["id"] not in search_ids(client, status="PUBLISHED", keyword="予約" + unique, sort="title_asc")
    response = client.patch(f"/api/articles/{future['id']}/status", json={"status": "DRAFT"})
    assert response.status_code == 200, response.text
    assert response.json()["is_scheduled"] is False
    assert response.json()["published_at"] is None

# テストケース2：ステータス×カテゴリ×タグ×キーワードの単独・複合検索
# 期待値：ステータス、カテゴリ、タグ、キーワードの4条件全てに一致する記事のみ取得できること。
def test_combined_filters(client, create_article, create_category, unique):
    category_a = create_category(unique, "a")
    category_b = create_category(unique, "b")
    tag_a = "filtera-" + unique
    tag_b = "filterb-" + unique
    keyword = "検索語" + unique
    target = create_article(title=keyword + "対象", status="PUBLISHED", category_id=category_a["id"], tag_names=[tag_a, tag_b])
    wrong_status = create_article(title=keyword + "下書き", status="DRAFT", category_id=category_a["id"], tag_names=[tag_a])
    wrong_category = create_article(title=keyword + "別カテゴリ", status="PUBLISHED", category_id=category_b["id"], tag_names=[tag_a])
    wrong_tag = create_article(title=keyword + "別タグ", status="PUBLISHED", category_id=category_a["id"], tag_names=[tag_b])
    wrong_keyword = create_article(title="対象外" + unique, status="PUBLISHED", category_id=category_a["id"], tag_names=[tag_a])
    tag_a_id = next(tag["id"] for tag in target["tags"] if tag["name"] == tag_a)
    all_test_ids = {a["id"] for a in (target, wrong_status, wrong_category, wrong_tag, wrong_keyword)}
    def matched(**params):
        return set(search_ids(client, **params)) & all_test_ids
    assert matched(status="PUBLISHED") == {target["id"], wrong_category["id"], wrong_tag["id"], wrong_keyword["id"]}
    assert matched(category_id=category_a["id"]) == {target["id"], wrong_status["id"], wrong_tag["id"], wrong_keyword["id"]}
    assert matched(tag_ids=[tag_a_id]) == {target["id"], wrong_status["id"], wrong_category["id"], wrong_keyword["id"]}
    assert matched(keyword=keyword) == {target["id"], wrong_status["id"], wrong_category["id"], wrong_tag["id"]}
    assert matched(status="PUBLISHED", category_id=category_a["id"], tag_ids=[tag_a_id], keyword=keyword) == {target["id"]}

# テストケース3：スラッグ重複・絵文字・改行を含む本文の保存と再取得
# 期待値：絵文字・改行を含む本文が保存され、再取得時に同一の内容が返却されること。
def test_article_slug_duplicate_and_unicode(client, create_article, unique):
    body = "絵文字😀🚀\n改行\n\nテスト"
    article = create_article(title="絵文字" + unique, body=body)
    assert article["body"] == body
    response = client.get(f"/api/articles/{article['id']}")
    assert response.status_code == 200, response.text
    assert response.json()["body"] == body
    assert response.json()["slug"] == article["slug"]
    duplicate = client.post(
        "/api/articles",
        json={"title": "重複", "slug": article["slug"]},
    )
    assert duplicate.status_code == 409, duplicate.text

# テストケース4：MySQLの接続文字コードと本文カラムの文字コードを確認
# 期待値：接続と保存先がutf8mb4であること。
def test_mysql_utf8mb4():
    with engine.connect() as conn:
        charset = conn.execute(text("SELECT @@character_set_connection")).scalar_one()
        assert charset.lower() == "utf8mb4"
        column = conn.execute(text("""
            SELECT CHARACTER_SET_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'article'
              AND COLUMN_NAME = 'body'
        """)).scalar_one()
        assert column.lower() == "utf8mb4"

# テストケース5：カテゴリ絞り込み・カテゴリ削除
# 期待値：指定カテゴリの記事のみ取得でき、カテゴリ削除後は「カテゴリなし」になること。
def test_category_filter_and_delete(client, create_article, create_category, unique):
    category = create_category(unique)
    included = create_article(category_id=category["id"])
    excluded = create_article(category_id=None)
    ids = search_ids(client, category_id=category["id"])
    assert included["id"] in ids
    assert excluded["id"] not in ids
    response = client.delete(f"/api/categories/{category['id']}")
    assert response.status_code == 204, response.text
    after = client.get(f"/api/articles/{included['id']}")
    assert after.status_code == 200, after.text
    assert after.json()["category_id"] is None
    assert after.json()["category"] is None

# テストケース6：複数タグの登録・タグによる絞り込み・タグ削除
# 期待値：複数タグが登録され、指定タグの記事のみ取得でき、タグ削除後は記事から削除されること。
def test_multiple_tags_filter_and_delete(client, create_article, unique):
    tag_a = "tag-a-" + unique
    tag_b = "tag-b-" + unique
    included = create_article(tag_names=[tag_a, tag_b])
    excluded = create_article(tag_names=["tag-c-" + unique])
    assert {tag["name"] for tag in included["tags"]} == {tag_a, tag_b}
    tag_a_id = next(tag["id"] for tag in included["tags"] if tag["name"] == tag_a)
    tag_b_id = next(tag["id"] for tag in included["tags"] if tag["name"] == tag_b)
    for tag_id in (tag_a_id, tag_b_id):
        ids = search_ids(client, tag_ids=[tag_id])
        assert included["id"] in ids
        assert excluded["id"] not in ids
    response = client.delete(f"/api/tags/{tag_a_id}")
    assert response.status_code == 204, response.text
    after = client.get(f"/api/articles/{included['id']}")
    assert after.status_code == 200, after.text
    assert {tag["id"] for tag in after.json()["tags"]} == {tag_b_id}
    assert included["id"] not in search_ids(client, tag_ids=[tag_a_id])

# テストケース7：並び替え・タイトル・更新日時・公開日時の順序を確認
# 期待値：タイトル昇順、更新日時降順、公開日時降順で取得できること。
def test_article_sort(client, create_article, unique):
    a = create_article(title="C" + unique, status="PUBLISHED")
    b = create_article(title="A" + unique, status="PUBLISHED")
    c = create_article(title="B" + unique, status="PUBLISHED")
    ids = {a["id"], b["id"], c["id"]}
    with SessionLocal() as db:
        base = datetime(2024, 1, 1)
        for article_id, updated_day, published_day in (
            (a["id"], 1, 3),
            (b["id"], 3, 1),
            (c["id"], 2, 2),
        ):
            article = db.get(Article, article_id)
            article.updated_at = base + timedelta(days=updated_day)
            article.published_at = base + timedelta(days=published_day)
        db.commit()
    def test_order(sort):
        return [article_id for article_id in search_ids(client, sort=sort) if article_id in ids]
    assert test_order("title_asc") == [b["id"], c["id"], a["id"]]
    assert test_order("updated_desc") == [b["id"], c["id"], a["id"]]
    assert test_order("published_desc") == [a["id"], c["id"], b["id"]]

# テストケース8：ステータス変更後の記事一覧取得APIの反映
# 期待値：ステータス変更後、記事一覧取得APIに変更が反映されること
def test_status_change_and_refetch(client, create_article):
    article = create_article(status="DRAFT")
    assert article["id"] in search_ids(client, status="DRAFT")
    response = client.patch(f"/api/articles/{article['id']}/status", json={"status": "PUBLISHED"})
    assert response.status_code == 200, response.text
    assert article["id"] in search_ids(client, status="PUBLISHED")
    assert article["id"] not in search_ids(client, status="DRAFT")

# テストケース9：記事・カテゴリ・タグ・スラッグを作成後にFastAPIを再起動し、DB内容を確認
# 期待値：作成した記事・カテゴリ・タグ・スラッグがDBに残っていること。
# 実施手順：①createで実行
#          ②FastAPIを手動で再起動
#          ③verifyで再実行
# 注意：本テストの確認用データは自動削除しないため、確認後に手動で削除する。
@pytest.mark.skipif(
    os.getenv("CMS_PERSISTENCE_PHASE") not in ("create", "verify"),
    reason="Set CMS_PERSISTENCE_PHASE=create or verify to run persistence check",
)
def test_data_persists_across_server_restart(client):
    phase = os.environ["CMS_PERSISTENCE_PHASE"]
    suffix = os.environ.get("CMS_PERSISTENCE_SUFFIX", "manual-restart-check")
    slug = "pytest-restart-" + suffix
    category_slug = "restart-" + suffix
    tag_name = "restart-" + suffix
    if phase == "create":
        category_response = client.post(
            "/api/categories",
            json={"name": "再起動確認" + suffix, "slug": category_slug},
        )
        assert category_response.status_code == 201, category_response.text
        response = client.post(
            "/api/articles",
            json={
                "title": "pytest-restart-persistence-check",
                "slug": slug,
                "body": "永続化確認",
                "category_id": category_response.json()["id"],
                "tag_names": [tag_name],
            },
        )
        assert response.status_code == 201, response.text
        assert get_db_article(response.json()["id"]) is not None
    else:
        with SessionLocal() as db:
            matches = db.scalars(select(Article).where(Article.slug == slug)).all()
            assert matches, "再起動後にテスト記事がDBに存在しません"
            article_id = matches[0].id
        response = client.get(f"/api/articles/{article_id}")
        assert response.status_code == 200, response.text
        assert response.json()["slug"] == slug
        assert response.json()["category"]["slug"] == category_slug
        assert tag_name in [tag["name"] for tag in response.json()["tags"]]
