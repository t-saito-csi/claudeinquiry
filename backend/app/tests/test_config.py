"""
設定管理 (app/config.py) のテスト。

Red-Green-Refactor:
  - Red  : config.py が存在しないため、インポートが失敗することを確認する。
  - Green: Settings クラスが環境変数を正しく読み込めることを確認する。
"""

import pytest
from pydantic import ValidationError

from app.config import Settings

_BASE = {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/inquiry_test_db",
    "SECRET_KEY": "a" * 32,
    "ENCRYPTION_KEY": "b" * 32,
}

# CI 環境変数がテストに漏れ込まないよう共通で削除する環境変数
_CI_ENV_VARS = [
    "DATABASE_URL",
    "SECRET_KEY",
    "ENCRYPTION_KEY",
    "ANTHROPIC_API_KEY",
    "FHIR_CLIENT_SECRET",
    "ALLOWED_ORIGINS",
    "ENVIRONMENT",
]


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """各テスト実行前に CI 環境変数を除去してテストを分離する。"""
    for key in _CI_ENV_VARS:
        monkeypatch.delenv(key, raising=False)


def test_settings_default_environment() -> None:
    """ENVIRONMENT のデフォルト値が 'development' であること。"""
    settings = Settings(**_BASE)
    assert settings.ENVIRONMENT == "development"


def test_settings_secret_key_min_length_passes() -> None:
    """SECRET_KEY が 32 文字以上のとき正常に生成されること。"""
    settings = Settings(**_BASE)
    assert len(settings.SECRET_KEY) >= 32


def test_settings_secret_key_too_short_raises() -> None:
    """SECRET_KEY が 31 文字以下のとき ValidationError が発生すること。"""
    with pytest.raises(ValidationError):
        Settings(**{**_BASE, "SECRET_KEY": "a" * 31})


def test_settings_encryption_key_too_short_raises() -> None:
    """ENCRYPTION_KEY が 31 文字以下のとき ValidationError が発生すること。"""
    with pytest.raises(ValidationError):
        Settings(**{**_BASE, "ENCRYPTION_KEY": "b" * 31})


def test_settings_database_url_required() -> None:
    """DATABASE_URL が未設定のとき ValidationError が発生すること。"""
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="a" * 32, ENCRYPTION_KEY="b" * 32)


def test_settings_is_development_true_when_development() -> None:
    """ENVIRONMENT が 'development' のとき is_development が True であること。"""
    settings = Settings(**{**_BASE, "ENVIRONMENT": "development"})
    assert settings.is_development is True


def test_settings_is_development_false_when_production() -> None:
    """ENVIRONMENT が 'production' のとき is_development が False であること。"""
    settings = Settings(
        **{
            **_BASE,
            "ENVIRONMENT": "production",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "FHIR_CLIENT_SECRET": "fhir-secret",
        }
    )
    assert settings.is_development is False


def test_settings_allowed_origins_default_is_empty_list() -> None:
    """ALLOWED_ORIGINS のデフォルト値が空リストであること。"""
    settings = Settings(**_BASE)
    assert settings.ALLOWED_ORIGINS == []


def test_settings_allowed_origins_parsed_from_comma_separated_string() -> None:
    """カンマ区切り文字列が正しくリストに変換されること。"""
    settings = Settings(
        **{
            **_BASE,
            "ALLOWED_ORIGINS": "https://a.example.com, https://b.example.com",
        }
    )
    assert settings.ALLOWED_ORIGINS == ["https://a.example.com", "https://b.example.com"]


def test_settings_invalid_environment_raises() -> None:
    """ENVIRONMENT に無効な値を指定すると ValidationError が発生すること。"""
    with pytest.raises(ValidationError):
        Settings(**{**_BASE, "ENVIRONMENT": "invalid_env"})  # type: ignore[arg-type]


def test_settings_production_requires_anthropic_api_key() -> None:
    """production 環境で ANTHROPIC_API_KEY が未設定のとき ValidationError が発生すること。"""
    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY is required"):
        Settings(
            **{
                **_BASE,
                "ENVIRONMENT": "production",
                "FHIR_CLIENT_SECRET": "fhir-secret",
            }
        )


def test_settings_production_requires_fhir_client_secret() -> None:
    """production 環境で FHIR_CLIENT_SECRET が未設定のとき ValidationError が発生すること。"""
    with pytest.raises(ValidationError, match="FHIR_CLIENT_SECRET is required"):
        Settings(
            **{
                **_BASE,
                "ENVIRONMENT": "production",
                "ANTHROPIC_API_KEY": "sk-ant-test",
            }
        )


def test_settings_production_all_required_fields_passes() -> None:
    """production 環境で必須フィールドがすべて設定されているとき正常に生成されること。"""
    settings = Settings(
        **{
            **_BASE,
            "ENVIRONMENT": "production",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "FHIR_CLIENT_SECRET": "fhir-secret",
        }
    )
    assert settings.ENVIRONMENT == "production"
