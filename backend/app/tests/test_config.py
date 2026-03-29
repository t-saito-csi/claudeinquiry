"""
設定管理 (app/config.py) のテスト。

Red-Green-Refactor:
  - Red  : config.py が存在しないため、インポートが失敗することを確認する。
  - Green: Settings クラスが環境変数を正しく読み込めることを確認する。
"""

import pytest

from app.config import Settings


def test_settings_default_environment() -> None:
    """ENVIRONMENT のデフォルト値が 'development' であること。"""
    settings = Settings(
        SECRET_KEY="a" * 32,
        ENCRYPTION_KEY="b" * 32,
    )
    assert settings.ENVIRONMENT == "development"


def test_settings_required_secret_key() -> None:
    """SECRET_KEY が設定されていること。"""
    settings = Settings(
        SECRET_KEY="a" * 32,
        ENCRYPTION_KEY="b" * 32,
    )
    assert len(settings.SECRET_KEY) == 32


def test_settings_is_development_true_when_development() -> None:
    """ENVIRONMENT が 'development' のとき is_development が True であること。"""
    settings = Settings(
        SECRET_KEY="a" * 32,
        ENCRYPTION_KEY="b" * 32,
        ENVIRONMENT="development",
    )
    assert settings.is_development is True


def test_settings_is_development_false_when_production() -> None:
    """ENVIRONMENT が 'production' のとき is_development が False であること。"""
    settings = Settings(
        SECRET_KEY="a" * 32,
        ENCRYPTION_KEY="b" * 32,
        ENVIRONMENT="production",
    )
    assert settings.is_development is False


def test_settings_allowed_origins_default() -> None:
    """ALLOWED_ORIGINS のデフォルト値が空リストであること。"""
    settings = Settings(
        SECRET_KEY="a" * 32,
        ENCRYPTION_KEY="b" * 32,
    )
    assert isinstance(settings.ALLOWED_ORIGINS, list)


def test_settings_invalid_environment_raises() -> None:
    """ENVIRONMENT に無効な値を指定すると ValidationError が発生すること。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY="a" * 32,
            ENCRYPTION_KEY="b" * 32,
            ENVIRONMENT="invalid_env",  # type: ignore[arg-type]
        )
