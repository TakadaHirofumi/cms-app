# 入力チェックとAPIデータ形式
from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
)
from models import ArticleStatus


TITLE_MAX_LENGTH = 200

# 記事作成・編集で共通する入力項目
class ArticleBase(BaseModel):
    title: str
    body: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        # 未入力チェック
        if not value.strip():
            raise ValueError(
                "タイトルを入力してください。"
            )

        # 文字数チェック
        if len(value) > TITLE_MAX_LENGTH:
            raise ValueError(
                "タイトルに201文字以上入力されているため、200文字までに減らして入力してください。"
            )

        return value.strip()

# 記事作成用スキーマ
class ArticleCreate(ArticleBase):
    pass

# 記事編集用スキーマ
class ArticleUpdate(ArticleBase):
    pass

# ステータス変更APIのリクエスト形式
class ArticleStatusUpdate(BaseModel):
    status: ArticleStatus

# APIレスポンスのデータ形式
class ArticleResponse(BaseModel):
    id: int
    title: str
    body: str | None
    status: ArticleStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
