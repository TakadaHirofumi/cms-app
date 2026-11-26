# 各テストで使用する認証済みクライアントとテストユーザー
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from database import SessionLocal
from main import app
from models import Article, User, UserRole


@pytest.fixture
def anonymous():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def make_user(anonymous):
    created_ids = []
    def create(role="EDITOR"):
        email = f"pytest-{uuid.uuid4().hex}@example.com"
        password = "Pytest1234!"
        response = anonymous.post("/api/auth/register", json={
            "email": email, "password": password, "display_name": "pytestユーザー"
        })
        assert response.status_code == 201, response.text
        user = response.json()
        created_ids.append(user["id"])
        assert user["role"] == "VIEWER"
        # テスト準備のみDBで権限を設定し、認証自体は実際のAPIを使用
        with SessionLocal() as db:
            db.get(User, user["id"]).role = UserRole(role)
            db.commit()
        response = anonymous.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return {**user, "role": role, "headers": {"Authorization": "Bearer " + response.json()["access_token"]}}
    yield create
    # テストユーザーの記事を先に削除し、外部キー制約を守る
    with SessionLocal() as db:
        for article in db.scalars(select(Article).where(Article.author_user_id.in_(created_ids))).all():
            db.delete(article)
        db.flush()
        for user_id in created_ids:
            user = db.get(User, user_id)
            if user is not None:
                db.delete(user)
        db.commit()

@pytest.fixture
def client(make_user):
    # 旧フェーズの全記事検索・編集テストはADMINとして実行
    with TestClient(app, headers=make_user("ADMIN")["headers"]) as test_client:
        yield test_client

@pytest.fixture
def persistence_client(anonymous):
    # 再起動確認では同じ専用ADMINを使用し、データを保持する
    email = os.environ.get("CMS_PERSISTENCE_EMAIL")
    password = os.environ.get("CMS_PERSISTENCE_PASSWORD")
    assert email and password, "再起動確認用ADMINの環境変数を設定してください"
    response = anonymous.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    with TestClient(app, headers={"Authorization": "Bearer " + response.json()["access_token"]}) as test_client:
        assert test_client.get("/api/auth/me").json()["role"] == "ADMIN"
        yield test_client
