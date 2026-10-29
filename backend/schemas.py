# 入力チェックとAPIデータ形式
import re
from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from models import ArticleStatus


# 記事タイトルの最大文字数
TITLE_MAX_LENGTH = 200
# スラッグの最大文字数
SLUG_MAX_LENGTH = 200
# カテゴリ名、タグ名の最大文字数
NAME_MAX_LENGTH = 30
# スラッグの入力値を検証する正規表現（英数字とハイフンのみ）
SLUG_PATTERN = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")

# カテゴリ作成用スキーマ
class CategoryCreate(BaseModel):
    name: str
    slug: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        # カテゴリ名の未入力・文字数チェック
        value = value.strip()
        if not value or len(value) > NAME_MAX_LENGTH:
            raise ValueError("カテゴリ名は30文字以内で入力してください。")
        return value

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        # スラッグの半角英数字・ハイフン、最大200文字チェック
        if len(value) > SLUG_MAX_LENGTH or not SLUG_PATTERN.fullmatch(value):
            raise ValueError("スラッグは200文字以内の英数字とハイフンで入力してください。")
        return value

# カテゴリ取得用スキーマ
class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(
        from_attributes=True
    )

# タグ取得用スキーマ
class TagResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(
        from_attributes=True
    )

# 記事作成・編集で共通する入力項目
class ArticleBase(BaseModel):
    title: str
    slug: str
    body: str | None = None
    category_id: int | None = None
    tag_names: list[str] = Field(default_factory=list)
    published_at: datetime | None = None

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

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        # スラッグの文字数・使用可能文字チェック
        if len(value) > SLUG_MAX_LENGTH or not SLUG_PATTERN.fullmatch(value):
            raise ValueError(
                "スラッグは200文字以内の英数字とハイフンで入力してください。"
            )
        return value

    @field_validator("tag_names")
    @classmethod
    def validate_tag_names(cls, values: list[str]) -> list[str]:
        # タグ名を検証し、同じ名前が複数ある場合は重複を除去
        names = []
        for name in values:
            name = name.strip()
            if not name or len(name) > NAME_MAX_LENGTH:
                raise ValueError("タグ名は30文字以内で入力してください。")
            if name not in names:
                names.append(name)
        return names

    @field_validator("published_at")
    @classmethod
    def validate_published_at(cls, value: datetime | None) -> datetime | None:
        # 公開日時はタイムゾーンなしの日本時間を受け付ける
        if value is not None and value.tzinfo is not None:
            raise ValueError("公開日時はタイムゾーンなしの日本時間で指定してください。")
        return value

# 記事作成用スキーマ
class ArticleCreate(ArticleBase):
    status: ArticleStatus = ArticleStatus.DRAFT

# 記事編集用スキーマ
class ArticleUpdate(ArticleBase):
    status: ArticleStatus

# ステータス変更APIのリクエスト形式
class ArticleStatusUpdate(BaseModel):
    status: ArticleStatus

# APIレスポンスのデータ形式
class ArticleResponse(BaseModel):
    id: int
    title: str
    slug: str
    body: str | None
    status: ArticleStatus
    published_at: datetime | None
    category_id: int | None
    category: CategoryResponse | None
    tags: list[TagResponse]
    created_at: datetime
    updated_at: datetime
    is_scheduled: bool = False

    model_config = ConfigDict(
        from_attributes=True
    )
