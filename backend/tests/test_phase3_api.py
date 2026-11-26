# CMSアプリのテストコード（フェーズ3版）
import uuid
import pytest
from sqlalchemy import select, func
from database import SessionLocal
from main import app
from models import Article, Comment, Revision


# テスト用記事の作成と削除を行う関数
@pytest.fixture
def make_article(client):
    created_ids = []

    # テスト用記事の作成
    def create(**kwargs):
        data = {
            "title": f"pytest-phase3-{uuid.uuid4().hex}",
            "slug": f"pytest-phase3-{uuid.uuid4().hex}",
            "body": "<p>テスト本文</p>",
            "status": "DRAFT",
            "category_id": None,
            "tag_names": [],
        }
        data.update(kwargs)
        response = client.post("/api/articles", json=data)
        assert response.status_code == 201, response.text
        article_id = response.json()["id"]
        created_ids.append(article_id)
        return response.json()

    # テストケースの関数に記事作成処理を渡す
    yield create

    # テスト終了後に記事を削除
    # comment・revisionは外部キーのON DELETE CASCADEで削除される想定
    with SessionLocal() as db:
        for article_id in created_ids:
            article = db.get(Article, article_id)
            if article is not None:
                db.delete(article)
        db.commit()

# DBに保存されているコメント数を取得
# 記事削除後も確認できるよう、article_idを条件にする
def count_db_comments(article_id):
    with SessionLocal() as db:
        return db.scalar(
            select(func.count(Comment.id)).where(Comment.article_id == article_id)
        )

# DBに保存されているリビジョン数を取得
def count_db_revisions(article_id):
    with SessionLocal() as db:
        return db.scalar(
            select(func.count(Revision.id)).where(Revision.article_id == article_id)
        )

# 記事のリビジョン一覧をAPIから取得する共通処理
def get_revisions(client, article_id):
    response = client.get(f"/api/articles/{article_id}/revisions")
    assert response.status_code == 200, response.text
    return response.json()

# 記事更新用のリクエストデータを作成する共通処理
# フェーズ2から引き継いだPUT APIの必須項目を含める
def update_article(client, article, *, title, body, status=None):
    article_id = article["id"]
    response = client.put(
        f"/api/articles/{article_id}",
        json={
            "title": title,
            "slug": article["slug"],
            "body": body,
            "status": status or article["status"],
            "published_at": article.get("published_at"),
            "category_id": article.get("category_id"),
            "tag_names": [tag["name"] for tag in article.get("tags", [])],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()

# テストケース1：公開済み記事へのコメント投稿・一覧取得
# 期待値：投稿時に201、一覧取得時に200が返り、投稿内容が一致すること。
def test_published_article_accepts_comment_and_lists_it(client, make_article):
    article = make_article(status="PUBLISHED")
    article_id = article["id"]
    author_name = "pytest投稿者"
    comment_body = "コメント投稿テスト\n2行目です。"

    # 公開済み記事にコメントを投稿
    response = client.post(
        f"/api/articles/{article_id}/comments",
        json={"author_name": author_name, "body": comment_body},
    )
    assert response.status_code == 201, response.text
    comment = response.json()
    assert comment["article_id"] == article_id
    assert comment["author_name"] == author_name
    assert comment["body"] == comment_body
    assert comment["id"] is not None

    # 投稿したコメントを一覧取得APIから確認
    response = client.get(f"/api/articles/{article_id}/comments")
    assert response.status_code == 200, response.text
    assert any(
        item["id"] == comment["id"]
        and item["author_name"] == author_name
        and item["body"] == comment_body
        for item in response.json()
    )
    assert count_db_comments(article_id) == 1

# テストケース2～3：下書き・アーカイブ済み記事へのコメント投稿拒否
# 期待値：どちらも403が返り、コメントがDBに保存されないこと。
@pytest.mark.parametrize("article_status", ["DRAFT", "ARCHIVED"])
def test_non_published_article_rejects_comment(client, make_article, article_status):
    article = make_article(status=article_status)
    article_id = article["id"]

    response = client.post(
        f"/api/articles/{article_id}/comments",
        json={"author_name": "pytest投稿者", "body": "投稿できないコメント"},
    )
    assert response.status_code == 403, response.text
    assert count_db_comments(article_id) == 0

    # コメント一覧にも登録されていないことを確認
    response = client.get(f"/api/articles/{article_id}/comments")
    assert response.status_code == 200, response.text
    assert response.json() == []

# テストケース4：記事削除に伴うコメントの連動削除
# 期待値：記事削除APIが204を返し、紐づくコメントもDBから削除されること。
def test_delete_article_cascades_to_comments(client, make_article):
    article = make_article(status="PUBLISHED")
    article_id = article["id"]

    # 同一記事にコメントを2件投稿
    for index in (1, 2):
        response = client.post(
            f"/api/articles/{article_id}/comments",
            json={"author_name": f"投稿者{index}", "body": f"コメント{index}"},
        )
        assert response.status_code == 201, response.text
    assert count_db_comments(article_id) == 2

    # 記事を削除して記事・コメントの両方がなくなることを確認
    response = client.delete(f"/api/articles/{article_id}")
    assert response.status_code == 204, response.text
    with SessionLocal() as db:
        assert db.get(Article, article_id) is None
    assert count_db_comments(article_id) == 0

# テストケース5：記事更新のたびにリビジョンが1件追加される
# 期待値：PUTによる更新1回につき履歴が1件増え、更新前の内容が保存されること。
def test_each_article_update_creates_one_revision(client, make_article):
    article = make_article(title="更新前タイトル", body="<p>更新前本文</p>")
    article_id = article["id"]
    initial_count = len(get_revisions(client, article_id))

    # 1回目の更新：更新前のタイトル・本文が履歴に保存される
    updated = update_article(
        client, article, title="1回目タイトル", body="<p>1回目本文</p>"
    )
    revisions = get_revisions(client, article_id)
    assert len(revisions) == initial_count + 1
    assert revisions[0]["title"] == "更新前タイトル"
    assert revisions[0]["body"] == "<p>更新前本文</p>"
    assert revisions[0]["status"] == "DRAFT"

    # 2回目の更新：さらに1件増え、直前の内容が保存される
    updated = update_article(
        client, updated, title="2回目タイトル", body="<p>2回目本文</p>"
    )
    revisions = get_revisions(client, article_id)
    assert len(revisions) == initial_count + 2
    assert revisions[0]["title"] == "1回目タイトル"
    assert revisions[0]["body"] == "<p>1回目本文</p>"
    assert count_db_revisions(article_id) == initial_count + 2
    assert updated["title"] == "2回目タイトル"

# テストケース6：過去のリビジョンからの復元と復元履歴の追加
# 期待値：タイトル・本文・ステータスが復元され、復元前の内容が新たに1件保存されること。
def test_restore_revision_restores_content_and_creates_revision(client, make_article):
    article = make_article(
        title="復元前の元タイトル", body="<p>復元前の元本文</p>", status="DRAFT"
    )
    article_id = article["id"]

    # 1回目の更新で元の内容を履歴に残す
    updated = update_article(
        client, article, title="変更後タイトル", body="<p>変更後本文</p>", status="PUBLISHED"
    )
    revisions = get_revisions(client, article_id)
    original_revision = next(
        item for item in revisions
        if item["title"] == "復元前の元タイトル"
        and item["body"] == "<p>復元前の元本文</p>"
        and item["status"] == "DRAFT"
    )
    revision_id = original_revision["id"]
    before_restore_count = len(revisions)
    assert updated["status"] == "PUBLISHED"

    # 元のリビジョンを指定して記事を復元
    response = client.post(
        f"/api/articles/{article_id}/revisions/{revision_id}/restore"
    )
    assert response.status_code == 200, response.text
    restored = response.json()
    assert restored["title"] == "復元前の元タイトル"
    assert restored["body"] == "<p>復元前の元本文</p>"
    assert restored["status"] == "DRAFT"
    assert restored["published_at"] is None

    # GET APIでも復元後の記事内容を確認
    response = client.get(f"/api/articles/{article_id}")
    assert response.status_code == 200, response.text
    assert response.json()["title"] == restored["title"]
    assert response.json()["body"] == restored["body"]
    assert response.json()["status"] == restored["status"]

    # 復元操作によって1件追加され、復元直前の内容が履歴に残る
    after_revisions = get_revisions(client, article_id)
    assert len(after_revisions) == before_restore_count + 1
    assert count_db_revisions(article_id) == before_restore_count + 1
    assert after_revisions[0]["title"] == "変更後タイトル"
    assert after_revisions[0]["body"] == "<p>変更後本文</p>"
    assert after_revisions[0]["status"] == "PUBLISHED"
    assert any(item["id"] == revision_id for item in after_revisions)
