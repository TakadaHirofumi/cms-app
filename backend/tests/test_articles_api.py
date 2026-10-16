# CMSアプリのテストコード
import os
import uuid
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import select
from database import SessionLocal
from main import app
from models import Article


# テストクライアントを作成
@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# テスト用記事の作成と削除を行う関数
@pytest.fixture
def make_article(client):
    created_ids = []

    # テスト用記事の作成
    def create():
        response = client.post(
            "/api/articles",
            json={"title": f"pytest-{uuid.uuid4().hex}", "body": "テスト本文"},
        )
        assert response.status_code == 201, response.text
        article_id = response.json()["id"]
        created_ids.append(article_id)
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

# DBから記事を取得
def get_db_article(article_id):
    with SessionLocal() as db:
        return db.get(Article, article_id)


# テストケース1：タイトルが空文字の記事を新規作成する。
# 期待値：422エラーになり、DBに保存されないこと。
def test_empty_title_create_is_rejected_and_not_saved(client):
    with SessionLocal() as db:
        before_ids = set(db.scalars(select(Article.id)).all())

    response = client.post("/api/articles", json={"title": "", "body": "本文"})
    assert response.status_code == 422, response.text

    with SessionLocal() as db:
        after_ids = set(db.scalars(select(Article.id)).all())
    assert after_ids == before_ids


# テストケース2：既存記事のタイトルを空文字に変更して保存する。
# 期待値：422エラーになり、DBの元データが維持されること。
def test_empty_title_update_is_rejected_and_unchanged(client, make_article):
    article_id = make_article()
    before = get_db_article(article_id)
    original_title, original_body = before.title, before.body

    # Adjust PUT to PATCH if your actual article-edit endpoint uses PATCH.
    response = client.put(
        f"/api/articles/{article_id}", json={"title": "", "body": "変更本文"}
    )
    assert response.status_code == 422, response.text
    after = get_db_article(article_id)
    assert after.title == original_title
    assert after.body == original_body


# テストケース3：ステータスをDRAFT→PUBLISHED→DRAFTに変更する。
# 期待値：公開日時が設定された後に解除されること。
def test_publish_then_draft(client, make_article):
    article_id = make_article()

    # DRAFTからPUBLISHEDへ変更
    response = client.patch(
        f"/api/articles/{article_id}/status", json={"status": "PUBLISHED"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PUBLISHED"
    assert response.json()["published_at"] is not None
    published = get_db_article(article_id)
    assert published.status.value == "PUBLISHED"
    assert published.published_at is not None

    # PUBLISHEDからDRAFTへ戻す
    response = client.patch(
        f"/api/articles/{article_id}/status", json={"status": "DRAFT"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "DRAFT"
    assert response.json()["published_at"] is None
    updated = get_db_article(article_id)
    assert updated.status.value == "DRAFT"
    assert updated.published_at is None


# テストケース4：ステータスをDRAFT→PUBLISHED→ARCHIVEDに変更する。
# 期待値：公開日時が設定された後に解除されること。
def test_publish_then_archived(client, make_article):
    article_id = make_article()

    # DRAFTからPUBLISHEDへ変更
    response = client.patch(
        f"/api/articles/{article_id}/status", json={"status": "PUBLISHED"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PUBLISHED"
    assert response.json()["published_at"] is not None
    published = get_db_article(article_id)
    assert published.status.value == "PUBLISHED"
    assert published.published_at is not None

    # PUBLISHEDからARCHIVEDへ変更
    response = client.patch(
        f"/api/articles/{article_id}/status", json={"status": "ARCHIVED"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ARCHIVED"
    assert response.json()["published_at"] is None
    updated = get_db_article(article_id)
    assert updated.status.value == "ARCHIVED"
    assert updated.published_at is None


# テストケース5：記事を削除する。
# 期待値：204が返り、対象レコードがDBから削除されること。
def test_delete_removes_database_row(client, make_article):
    article_id = make_article()
    assert get_db_article(article_id) is not None
    response = client.delete(f"/api/articles/{article_id}")
    assert response.status_code == 204, response.text
    assert get_db_article(article_id) is None


# テストケース6：記事を作成後にFastAPIを再起動し、DB内容を確認する。
# 期待値：作成した記事がDBに残っていること。
# 実施手順：①createで記事を作成
#          ②FastAPIを手動で再起動
#          ③verifyでDBとAPIを確認
@pytest.mark.skipif(
    os.getenv("CMS_PERSISTENCE_PHASE") not in ("create", "verify"),
    reason="Set CMS_PERSISTENCE_PHASE=create or verify to run persistence check",
)
def test_data_persists_across_server_restart(client):
    phase = os.environ["CMS_PERSISTENCE_PHASE"]
    title = os.environ.get("CMS_PERSISTENCE_TITLE", "pytest-restart-persistence-check")
    if phase == "create":
        response = client.post("/api/articles", json={"title": title, "body": "永続化確認"})
        assert response.status_code == 201, response.text
        assert get_db_article(response.json()["id"]) is not None
    else:
        with SessionLocal() as db:
            matches = db.scalars(select(Article).where(Article.title == title)).all()
        assert matches, "再起動後にテスト記事がDBに存在しません"