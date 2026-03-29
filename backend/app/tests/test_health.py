"""
ヘルスチェックエンドポイントのテスト。

Red-Green-Refactor:
  - Red  : このテストはCI設定確認時に最初に失敗させることで、CIパイプラインが
           テスト失敗を正しく検出できることを確認する。
  - Green: /health エンドポイントが {"status": "ok"} を返すことを確認する。
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check_returns_200() -> None:
    """GETリクエストで /health が HTTP 200 を返すこと。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_response_body() -> None:
    """GETリクエストで /health が {"status": "ok"} を返すこと。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert body == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_content_type() -> None:
    """/health のレスポンスContent-TypeがJSONであること。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert "application/json" in response.headers["content-type"]
