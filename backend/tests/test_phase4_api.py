# CMSアプリのテストコード（フェーズ4版）
import os
import uuid
import pytest
from datetime import datetime, timedelta
from time import perf_counter
from sqlalchemy import select
from database import SessionLocal
from models import Article, Category, Tag, User


def payload(**kwargs):
    data = {"title": f"pytest-phase4-{uuid.uuid4().hex}", "slug": f"pytest-{uuid.uuid4().hex}",
            "body": "テスト本文", "status": "DRAFT", "category_id": None, "tag_names": []}
    data.update(kwargs)
    return data

def create_article(client, user, **kwargs):
    response = client.post("/api/articles", headers=user["headers"], json=payload(**kwargs))
    assert response.status_code == 201, response.text
    assert response.json()["author_user_id"] == user["id"]
    return response.json()

def update_data(article):
    return payload(title="更新後タイトル", slug=article["slug"], status=article["status"],
                   published_at=article["published_at"], category_id=article["category_id"],
                   tag_names=[t["name"] for t in article["tags"]])

# テストケース1～3：未認証・VIEWER権限ユーザー・EDITOR権限の他ユーザーによる記事操作の拒否
# 期待値：未認証は401、VIEWER権限ユーザー・EDITOR権限の他ユーザーは403が返り、記事のタイトル・ステータスが維持されること。
# 　　　　未認証・VIEWER権限ユーザーについては新規作成も拒否されること。
@pytest.mark.parametrize("role,expected", [(None, 401), ("VIEWER", 403), ("EDITOR", 403)])
def test_article_write_denied(anonymous, make_user, role, expected):
    owner = make_user()
    article = create_article(anonymous, owner)
    headers = make_user(role)["headers"] if role else {}
    url = f"/api/articles/{article['id']}"
    if role != "EDITOR":
        assert anonymous.post("/api/articles", headers=headers, json=payload()).status_code == expected
    for method, path, data in [("PUT", url, update_data(article)), ("PATCH", url+"/status", {"status":"PUBLISHED"}), ("DELETE", url, None)]:
        response = anonymous.request(method, path, headers=headers, json=data)
        assert response.status_code == expected, response.text
    with SessionLocal() as db:
        row = db.get(Article, article["id"])
        assert row.title == article["title"] and row.status.value == "DRAFT"

# テストケース4～5：EDITOR権限ユーザー・ADMIN権限ユーザーによる記事の更新・ステータス変更・削除
# 期待値：EDITOR権限ユーザーは自分の記事、ADMIN権限ユーザーは自分と他ユーザーの記事を操作でき、更新・ステータス変更は200、削除は204が返ること。
# 　　　　更新後のタイトルが一致し、削除後はDBに記事が存在しないこと。
@pytest.mark.parametrize("role", ["EDITOR", "ADMIN"])
def test_article_write_allowed(anonymous, make_user, role):
    actor = make_user(role)
    owners = [actor] if role == "EDITOR" else [make_user(), make_user(), actor]
    for owner in owners:
        article = create_article(anonymous, owner)
        url = f"/api/articles/{article['id']}"
        response = anonymous.put(url, headers=actor["headers"], json=update_data(article))
        assert response.status_code == 200, response.text
        assert response.json()["title"] == "更新後タイトル"
        assert anonymous.patch(url+"/status", headers=actor["headers"], json={"status":"PUBLISHED"}).status_code == 200
        assert anonymous.delete(url, headers=actor["headers"]).status_code == 204
        with SessionLocal() as db:
            assert db.get(Article, article["id"]) is None

# テストケース6～9：記事の公開状態別の閲覧権限・コメント投稿制御
# 期待値：公開済み記事は全員が閲覧でき、下書き・アーカイブ・予約中の記事は作成者本人であるEDITOR権限ユーザーとADMIN権限ユーザーのみ閲覧できること。
# 　　　　詳細取得は閲覧可能なら200、不可なら404、一覧取得は200で権限に応じた記事のみ含まれること。
# 　　　　コメント投稿は公開済みなら201、それ以外は権限にかかわらず403が返ること。
@pytest.mark.parametrize("status,scheduled", [("DRAFT",False),("ARCHIVED",False),("PUBLISHED",True),("PUBLISHED",False)])
def test_article_visibility(anonymous, make_user, status, scheduled):
    owner, other, viewer, admin = make_user(), make_user(), make_user("VIEWER"), make_user("ADMIN")
    public = status == "PUBLISHED" and not scheduled
    article = create_article(anonymous, owner, status=status, published_at=(datetime.now()+timedelta(days=1 if scheduled else -1)).isoformat() if status=="PUBLISHED" else None)
    for user in [None, viewer, other, owner, admin]:
        headers = user["headers"] if user else {}
        allowed = public or user in (owner, admin)
        response = anonymous.get(f"/api/articles/{article['id']}", headers=headers)
        assert response.status_code == (200 if allowed else 404), response.text
        response = anonymous.get("/api/articles", headers=headers, params={"keyword":article["title"]})
        assert response.status_code == 200
        assert (article["id"] in [a["id"] for a in response.json()]) == allowed
        response = anonymous.post(f"/api/articles/{article['id']}/comments", headers=headers, json={"author_name":"投稿者", "body":"確認"})
        assert response.status_code == (201 if public else 403), response.text

# テストケース10～11：カテゴリ・タグの一覧取得・作成・削除の認証制御
# 期待値：未認証でも一覧取得は200、作成・削除は未認証なら401、VIEWER権限ユーザーなら403が返ること。
# 　　　　EDITOR権限ユーザーによる作成は200または201、削除は204が返ること。
@pytest.mark.parametrize("path,model", [("categories",Category),("tags",Tag)])
def test_classification_auth(anonymous, make_user, path, model):
    url = "/api/"+path
    name = "pytest-"+uuid.uuid4().hex[:20]
    editor, viewer = make_user(), make_user("VIEWER")
    try:
        assert anonymous.get(url).status_code == 200
        for headers, expected in [({},401),(viewer["headers"],403)]:
            assert anonymous.post(url, headers=headers, json={"name":name}).status_code == expected
        response = anonymous.post(url, headers=editor["headers"], json={"name":name})
        assert response.status_code in (200,201), response.text
        target = url+"/"+str(response.json()["id"])
        assert anonymous.delete(target).status_code == 401
        assert anonymous.delete(target, headers=viewer["headers"]).status_code == 403
        assert anonymous.delete(target, headers=editor["headers"]).status_code == 204
    finally:
        with SessionLocal() as db:
            for row in db.scalars(select(model).where(model.name==name)).all():
                db.delete(row)
            db.commit()

# テストケース12：リビジョン一覧取得・復元の認証と所有者制限
# 期待値：未認証は401、VIEWER権限ユーザーとEDITOR権限の他ユーザーは403、作成者本人であるEDITOR権限ユーザーとADMIN権限ユーザーは一覧取得・復元ともに200が返ること。
def test_revision_auth(anonymous, make_user):
    owner = make_user()
    article = create_article(anonymous, owner)
    url = f"/api/articles/{article['id']}"
    assert anonymous.put(url, headers=owner["headers"], json=update_data(article)).status_code == 200
    url += "/revisions"
    response = anonymous.get(url, headers=owner["headers"])
    assert response.status_code == 200
    restore = url+f"/{response.json()[0]['id']}/restore"
    for headers, expected in [({},401),(make_user("VIEWER")["headers"],403),(make_user()["headers"],403)]:
        assert anonymous.get(url, headers=headers).status_code == expected
        assert anonymous.post(restore, headers=headers).status_code == expected
    for actor in [owner, make_user("ADMIN")]:
        assert anonymous.get(url, headers=actor["headers"]).status_code == 200
        assert anonymous.post(restore, headers=actor["headers"]).status_code == 200

# テストケース13：コメント通知の取得・記事単位の既読更新・一括既読
# 期待値：未認証の未読件数取得は401、記事作成者の未読件数はコメント投稿後に0件から2件となり、他ユーザーは0件のままであること。
# 　　　　通知一覧の未読コメントIDが一致し、他ユーザーの既読更新は404が返ること。
# 　　　　記事作成者の同一記事への既読更新を2回行っても200が返り、未読件数が1件となり、対象記事のコメントのみ既読になること。
# 　　　　一括既読は200が返り、未読件数が0件になること。
def test_notifications(anonymous, make_user):
    owner, other = make_user(), make_user()
    headers = owner["headers"]
    articles = [create_article(anonymous, owner, status="PUBLISHED") for _ in range(2)]
    count_url = "/api/notifications/unread-count"
    assert anonymous.get(count_url).status_code == 401
    assert anonymous.get(count_url, headers=headers).json()["unread_count"] == 0
    comments = []
    for article in articles:
        response = anonymous.post(f"/api/articles/{article['id']}/comments", json={"author_name":"匿名投稿者", "body":"通知確認"})
        assert response.status_code == 201, response.text
        comments.append(response.json()["id"])
    assert anonymous.get(count_url, headers=headers).json()["unread_count"] == 2
    assert anonymous.get(count_url, headers=other["headers"]).json()["unread_count"] == 0
    items = anonymous.get("/api/notifications", headers=headers).json()
    assert {i["comment_id"] for i in items if not i["is_read"]} == set(comments)
    url = f"/api/notifications/articles/{articles[0]['id']}/read"
    assert anonymous.patch(url, headers=other["headers"], json={"comment_ids":comments}).status_code == 404
    for _ in range(2):
        response = anonymous.patch(url, headers=headers, json={"comment_ids":comments})
        assert response.status_code == 200, response.text
        assert response.json()["unread_count"] == 1
    items = anonymous.get("/api/notifications", headers=headers).json()
    assert {i["comment_id"] for i in items if i["is_read"]} == {comments[0]}
    response = anonymous.patch("/api/notifications/read-all", headers=headers)
    assert response.status_code == 200 and response.json()["unread_count"] == 0

# テストケース14：JWT認証・ログインエラーの統一・パスワードのハッシュ保存
# 期待値：DBのパスワードハッシュが$2で始まり、誤ったパスワードと未登録メールアドレスでは401と共通エラーメッセージが返ること。
# 　　　　正常なJWTで本人のユーザーIDを取得でき、不正なJWTでは401が返ること。
def test_login(anonymous, make_user):
    user = make_user()
    with SessionLocal() as db:
        assert db.get(User,user["id"]).password_hash.startswith("$2")
    for email in [user["email"], f"unknown-{uuid.uuid4().hex}@example.com"]:
        response = anonymous.post("/api/auth/login", json={"email":email,"password":"Wrong1234"})
        assert response.status_code == 401
        assert response.json()["detail"] == "メールアドレスまたはパスワードが正しくありません"
    assert anonymous.get("/api/auth/me", headers=user["headers"]).json()["id"] == user["id"]
    assert anonymous.get("/api/auth/me", headers={"Authorization":"Bearer invalid"}).status_code == 401

# テストケース15：100件規模の記事一覧・検索・並び替えの性能確認
# 期待値：一覧・キーワード検索・タイトル昇順ではテスト記事100件、公開ステータスとの複合検索では50件が取得されること。
# 　　　　各APIが200を返し、対象記事ID・タイトル昇順が期待値と一致し、応答時間が設定上限（既定2秒）以内であること。
def test_100_articles_performance(anonymous, make_user):
    owner = make_user()
    prefix = "pytest-perf-"+uuid.uuid4().hex
    ids = []
    for i in reversed(range(100)):
        article = create_article(anonymous, owner, title=f"{prefix}-{i:03d}", status="PUBLISHED" if i%2==0 else "DRAFT")
        ids.append(article["id"])
    limit = float(os.getenv("CMS_API_MAX_SECONDS", "2.0"))
    for params, expected in [({},set(ids)), ({"keyword":prefix},set(ids)), ({"keyword":prefix,"status":"PUBLISHED"},set(ids[1::2])), ({"keyword":prefix,"sort":"title_asc"},set(ids))]:
        start = perf_counter()
        response = anonymous.get("/api/articles", headers=owner["headers"], params=params)
        elapsed = perf_counter()-start
        assert response.status_code == 200, response.text
        rows = [a for a in response.json() if a["id"] in ids]
        assert {a["id"] for a in rows} == expected
        if params.get("sort") == "title_asc":
            assert [a["title"] for a in rows] == sorted(a["title"] for a in rows)
        print(f"一覧API {params}: {elapsed:.3f}秒")
        assert elapsed <= limit, f"{elapsed:.3f}秒 > {limit}秒"

# テストケース16：公開日時の分単位判定の境界値確認
# 期待値：現在と同じ分の59秒を公開日時に指定した記事は公開済みと判定され、詳細取得は200、is_scheduledはFalse、コメント投稿は201が返ること。
def test_publication_minute_boundary(anonymous, make_user):
    owner = make_user()
    article = create_article(anonymous, owner, status="PUBLISHED",
                             published_at=datetime.now().replace(second=59, microsecond=0).isoformat())
    url = f"/api/articles/{article['id']}"
    response = anonymous.get(url)
    assert response.status_code == 200, response.text
    assert response.json()["is_scheduled"] is False
    response = anonymous.post(url+"/comments", json={"author_name":"投稿者", "body":"公開日時確認"})
    assert response.status_code == 201, response.text

# テストケース17：ユーザー一覧取得・権限変更の管理者制限
# 期待値：ユーザー一覧取得は未認証なら401、EDITORなら403、ADMINなら200が返ること。
# 　　　　EDITORの権限変更は403、ADMINの権限変更は200が返り、変更後の本人情報にもEDITOR権限が反映されること。
def test_user_role_management(anonymous, make_user):
    admin, editor, viewer = make_user("ADMIN"), make_user(), make_user("VIEWER")
    url = f"/api/users/{viewer['id']}/role"
    assert anonymous.get("/api/users").status_code == 401
    assert anonymous.get("/api/users", headers=editor["headers"]).status_code == 403
    assert anonymous.get("/api/users", headers=admin["headers"]).status_code == 200
    assert anonymous.patch(url, headers=editor["headers"], json={"role":"EDITOR"}).status_code == 403
    response = anonymous.patch(url, headers=admin["headers"], json={"role":"EDITOR"})
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "EDITOR"
    assert anonymous.get("/api/auth/me", headers=viewer["headers"]).json()["role"] == "EDITOR"
