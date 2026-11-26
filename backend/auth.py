# JWT認証・パスワード検証・ユーザー権限判定
import os
import bcrypt
import jwt

from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserRole


# JWT署名鍵は.env(環境変数)から取得
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30
bearer = HTTPBearer(auto_error=False)

# bcryptでパスワードをハッシュ化・検証する
def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=422, detail="パスワードはUTF-8で72バイト以内にしてください")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False

# ユーザーIDをJWTのsubに格納し30分後に失効させる
def create_access_token(user_id: int) -> str:
    if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEYを32文字以上で設定してください")
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "iat": now,
                       "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES)},
                      JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

# Bearerトークンがあれば検証し、現在のユーザーを取得
def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db)
) -> User | None:
    if credentials is None:
        return None
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="認証が必要です", headers={"WWW-Authenticate": "Bearer"})
    if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEYを32文字以上で設定してください")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="認証が必要です", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="認証が必要です", headers={"WWW-Authenticate": "Bearer"})
    return user

# ログイン必須APIで使用
def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="認証が必要です", headers={"WWW-Authenticate": "Bearer"})
    return user

# 記事の作成・編集ができる権限を確認
def require_editor(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.EDITOR):
        raise HTTPException(status_code=403, detail="操作権限がありません")
    return user

# 管理者権限を確認
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    return user

# ADMINは全記事、EDITORは自分の記事のみ変更可能
def ensure_article_owner(user: User, article) -> None:
    if user.role != UserRole.ADMIN and article.author_user_id != user.id:
        raise HTTPException(status_code=403, detail="他のユーザーの記事は操作できません")
