"""
環境変数管理モジュール。

pydantic-settings を使用して環境変数を型安全に読み込む。
本番環境では SECRET_KEY と ENCRYPTION_KEY を KMS 経由で取得すること。
"""

from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定。

    環境変数または .env ファイルから値を読み込む。
    必須フィールド(SECRET_KEY, ENCRYPTION_KEY)が未設定の場合は起動時に例外を送出する。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -----------------------------------------------
    # Database
    # -----------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/inquiry_db"

    # -----------------------------------------------
    # Redis
    # -----------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # -----------------------------------------------
    # Security
    # -----------------------------------------------
    SECRET_KEY: Annotated[str, Field(min_length=32)]
    ENCRYPTION_KEY: Annotated[str, Field(min_length=32)]

    # -----------------------------------------------
    # Claude API
    # -----------------------------------------------
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # -----------------------------------------------
    # FHIR
    # -----------------------------------------------
    FHIR_SERVER_URL: str = "https://fhir.hospital.example.com/fhir/R4"
    FHIR_CLIENT_ID: str = ""
    FHIR_CLIENT_SECRET: str = ""

    # -----------------------------------------------
    # App
    # -----------------------------------------------
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    ALLOWED_ORIGINS: list[str] = Field(default_factory=list)

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        """カンマ区切り文字列をリストに変換する。

        環境変数でカンマ区切りで複数オリジンを指定できるようにする。
        例: ALLOWED_ORIGINS=https://a.example.com,https://b.example.com
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    @property
    def is_development(self) -> bool:
        """開発環境であるかどうかを返す。"""
        return self.ENVIRONMENT == "development"
