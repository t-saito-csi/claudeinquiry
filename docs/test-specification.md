# テスト仕様書
## デジタル問診システム (Medical Inquiry System)

| 項目 | 内容 |
|------|------|
| 文書バージョン | 1.0.0 |
| 作成日 | 2026-03-28 |
| テストフレームワーク | pytest（バックエンド）/ Vitest + Testing Library（フロントエンド）/ Playwright（E2E） |

---

## 目次

1. [テスト戦略・方針](#1-テスト戦略方針)
2. [テストレベルと分類](#2-テストレベルと分類)
3. [テスト環境・ツール](#3-テスト環境ツール)
4. [テストデータ設計](#4-テストデータ設計)
5. [認証APIテスト (AUTH)](#5-認証apiテスト-auth)
6. [患者向けAPIテスト (PAT)](#6-患者向けapiテスト-pat)
7. [受付スタッフAPIテスト (REC)](#7-受付スタッフapiテスト-rec)
8. [医師用ダッシュボードAPIテスト (DASH)](#8-医師用ダッシュボードapiテスト-dash)
9. [管理者APIテスト (ADM)](#9-管理者apiテスト-adm)
10. [サービス層テスト (SVC)](#10-サービス層テスト-svc)
11. [セキュリティテスト (SEC)](#11-セキュリティテスト-sec)
12. [フロントエンドテスト (FE)](#12-フロントエンドテスト-fe)
13. [E2Eテスト (E2E)](#13-e2eテスト-e2e)
14. [性能テスト (PERF)](#14-性能テスト-perf)
15. [アクセシビリティテスト (A11Y)](#15-アクセシビリティテスト-a11y)
16. [品質基準・合格条件](#16-品質基準合格条件)
17. [テスト実施計画](#17-テスト実施計画)

---

## 1. テスト戦略・方針

### 1.1 基本方針

| 方針 | 内容 |
|------|------|
| **Red-Green-Refactor** | テストが失敗する状態から始める。テストなしのコミット禁止 |
| **実際の動作検証** | `assert True` / `expect(true).toBe(true)` のような無意味なアサーション禁止 |
| **実データベース使用** | バックエンドは実PostgreSQL必須。モックDB禁止 |
| **最小限のモック** | 外部API（Claude API / NEC MegaOakHR）のみモック対象。内部ロジックはモックしない |
| **境界値・異常系の網羅** | 正常系だけでなく、境界値・異常系・エラーケースを必ずテストする |
| **医療データの安全性最優先** | 暗号化・RBAC・監査ログは特にテストを厚くする |

### 1.2 テスト対象外

- インフラ（AWS ECS / RDS のプロビジョニング自体）
- NEC MegaOakHR 本番環境との実接続
- Claude API 本番課金の動作確認

### 1.3 ハードコーディング禁止事項

```python
# ❌ 禁止: テストを通すためのハードコード
def get_ai_summary(session_id: str) -> str:
    if session_id == "test-session-id":  # テスト用の特別分岐
        return "固定サマリー"
    ...

# ✅ 正しい: 実際のロジックを検証
async def test_ai_summary_generation(client, session_with_completed_response):
    response = await client.get(f"/api/v1/dashboard/sessions/{session_with_completed_response.session_id}")
    assert response.status_code == 200
    assert response.json()["data"]["ai_summary"]["status"] == "completed"
    assert len(response.json()["data"]["ai_summary"]["symptom_summary"]) > 0
```

---

## 2. テストレベルと分類

```
        ┌──────────────────────────────────┐
        │   E2Eテスト (Playwright)          │ ← 少数・重要シナリオのみ
        ├──────────────────────────────────┤
        │   統合テスト (pytest / Vitest)    │ ← API全エンドポイント
        ├──────────────────────────────────┤
        │   単体テスト (pytest / Vitest)    │ ← サービス層・コンポーネント
        └──────────────────────────────────┘
```

| レベル | 対象 | ツール | 実行頻度 |
|--------|------|--------|---------|
| 単体テスト | サービス層・ユーティリティ・コンポーネント | pytest, Vitest | コミット毎 |
| 統合テスト | APIエンドポイント（実DB） | pytest + httpx | コミット毎 |
| E2Eテスト | 主要ユーザーフロー | Playwright | PR毎・デプロイ前 |
| 性能テスト | レスポンスタイム・同時接続 | Locust | リリース前 |
| セキュリティテスト | 認証・認可・暗号化・OWASP | pytest + 手動 | リリース前 |
| アクセシビリティテスト | WCAG 2.1 AA準拠 | axe-playwright | リリース前 |

---

## 3. テスト環境・ツール

### 3.1 バックエンドテスト環境

```
テスト用PostgreSQL: localhost:5433 / inquiry_test
テスト用Redis:      localhost:6380
Claude API:         モック（respx）
NEC MegaOakHR:      モック（respx）
```

**`.env.test` の設定値:**

```env
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5433/inquiry_test
REDIS_URL=redis://localhost:6380/1
SECRET_KEY=test-secret-key-32-bytes-minimum!!
ENCRYPTION_KEY=dGVzdC1lbmNyeXB0aW9uLWtleS0zMmI=
ANTHROPIC_API_KEY=test-anthropic-key
CLAUDE_MODEL=claude-sonnet-4-6
FHIR_SERVER_URL=http://localhost:9999/fhir/R4
ENVIRONMENT=test
```

### 3.2 テストツール一覧

**バックエンド:**

| ツール | 用途 | バージョン |
|--------|------|---------|
| pytest | テストランナー | 8.x |
| pytest-asyncio | 非同期テスト | latest |
| pytest-cov | カバレッジ計測 | latest |
| httpx | 非同期HTTPクライアント（APIテスト） | latest |
| factory-boy | テストデータファクトリ | latest |
| respx | 外部HTTPモック（Claude API / FHIR） | latest |
| Faker | フェイクデータ生成 | latest |

**フロントエンド:**

| ツール | 用途 |
|--------|------|
| Vitest | テストランナー |
| @testing-library/react | コンポーネントテスト |
| @testing-library/user-event | ユーザー操作シミュレーション |
| MSW (Mock Service Worker) | APIモック |
| Playwright | E2Eテスト |
| @axe-core/playwright | アクセシビリティ自動検査 |

### 3.3 テスト実行コマンド

```bash
# バックエンド - 全テスト
cd backend && pytest --cov=app --cov-report=term-missing -v

# バックエンド - カテゴリ別
pytest tests/api/test_auth.py -v
pytest tests/api/ -v                    # 全APIテスト
pytest tests/services/ -v               # サービス層テスト
pytest -m security -v                   # セキュリティテストのみ

# フロントエンド - 単体・統合
cd frontend && npm run test

# E2E
cd frontend && npx playwright test
npx playwright test --project=chromium  # Chromeのみ

# 性能テスト
cd tests/performance && locust -f locustfile.py --host=http://localhost:8000
```

### 3.4 conftest.py の構成

```python
# backend/tests/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.main import app
from app.core.database import Base
from tests.factories import StaffUserFactory, DepartmentFactory, PatientFactory

DATABASE_URL_TEST = "postgresql+asyncpg://test:test@localhost:5433/inquiry_test"

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(DATABASE_URL_TEST, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine):
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()  # 各テスト後にロールバック

@pytest_asyncio.fixture
async def client(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

@pytest_asyncio.fixture
async def doctor_client(client, db_session):
    """ログイン済み医師クライアント"""
    doctor = await StaffUserFactory.create(role="doctor", db=db_session)
    response = await client.post("/api/v1/auth/login", json={
        "email": doctor.email, "password": "Test1234!"
    })
    token = response.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client

@pytest_asyncio.fixture
async def admin_client(client, db_session):
    """ログイン済み管理者クライアント"""
    admin = await StaffUserFactory.create(role="admin", db=db_session)
    response = await client.post("/api/v1/auth/login", json={
        "email": admin.email, "password": "Test1234!"
    })
    token = response.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
```

---

## 4. テストデータ設計

### 4.1 Factoryクラス

```python
# backend/tests/factories.py

import factory
from factory.faker import Faker
from app.models import StaffUser, Patient, Department, InquirySession
from app.core.security import hash_password, encrypt_field

class DepartmentFactory(factory.Factory):
    class Meta:
        model = Department
    id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"診療科{n}")
    code = factory.Sequence(lambda n: f"dept_{n}")
    display_order = factory.Sequence(lambda n: n)
    is_active = True

class StaffUserFactory(factory.Factory):
    class Meta:
        model = StaffUser
    id = factory.LazyFunction(uuid4)
    email = factory.Sequence(lambda n: f"staff{n}@hospital.test")
    password_hash = factory.LazyFunction(lambda: hash_password("Test1234!"))
    full_name = Faker("name", locale="ja_JP")
    role = "doctor"
    department_ids = factory.List([])
    is_active = True
    failed_login_count = 0

class PatientFactory(factory.Factory):
    class Meta:
        model = Patient
    id = factory.LazyFunction(uuid4)
    external_patient_id = factory.Sequence(lambda n: f"{n:06d}")
    # 暗号化フィールドはファクトリで暗号化済みバイト列を生成
    name_encrypted, name_iv = factory.LazyFunction(
        lambda: encrypt_field("田中 花子")
    )
    gender = "female"
```

### 4.2 標準テストデータ

以下のマスタデータはconftest.pyのsessionスコープフィクスチャで一度作成し、全テストで共用する。

| データ種別 | 内容 |
|-----------|------|
| 診療科 | 内科(naika)・外科(geka)・産婦人科(sanka_fujinka)・小児科(shonika) |
| フォーム定義 | 各診療科につきpublished版1件・draft版1件 |
| スタッフ | admin×1・doctor×2（各科担当）・nurse×1・reception×1 |
| 患者 | 10名（アレルギーあり3名・服薬リスクあり2名） |

---

## 5. 認証APIテスト (AUTH)

### TC-AUTH-001: 正常ログイン

| 項目 | 内容 |
|------|------|
| 優先度 | 高 |
| 種別 | 統合テスト |
| エンドポイント | `POST /api/v1/auth/login` |

**前提条件:** 有効なスタッフアカウント（doctor）が存在する

```python
async def test_login_success_returns_access_token(client, db_session):
    doctor = await StaffUserFactory.create(role="doctor", db=db_session)

    response = await client.post("/api/v1/auth/login", json={
        "email": doctor.email,
        "password": "Test1234!"
    })

    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900
    assert data["user"]["role"] == "doctor"
    assert data["user"]["email"] == doctor.email
    # リフレッシュトークンがHttpOnly Cookieにセットされていること
    assert "refresh_token" in response.cookies
    cookie = response.cookies.get("refresh_token")
    assert cookie is not None
```

---

### TC-AUTH-002: パスワード不一致でログイン失敗

| 優先度 | 高 | 種別 | 統合テスト |
|--------|----|----|----------|

```python
async def test_login_fails_with_wrong_password(client, db_session):
    doctor = await StaffUserFactory.create(db=db_session)

    response = await client.post("/api/v1/auth/login", json={
        "email": doctor.email,
        "password": "WrongPassword!"
    })

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "INVALID_CREDENTIALS"
    assert "access_token" not in response.json().get("data", {})
```

---

### TC-AUTH-003: 5回失敗でアカウントロック

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_account_locks_after_5_failed_attempts(client, db_session):
    doctor = await StaffUserFactory.create(db=db_session)

    for i in range(5):
        resp = await client.post("/api/v1/auth/login", json={
            "email": doctor.email, "password": "WrongPassword!"
        })
        assert resp.status_code == 401

    # 6回目: 正しいパスワードでもロック
    response = await client.post("/api/v1/auth/login", json={
        "email": doctor.email, "password": "Test1234!"
    })
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"

    # DBのlocked_untilが設定されていることを確認
    await db_session.refresh(doctor)
    assert doctor.locked_until is not None
    assert doctor.locked_until > datetime.utcnow()
```

---

### TC-AUTH-004: 無効アカウントのログイン拒否

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_login_fails_for_inactive_account(client, db_session):
    inactive_staff = await StaffUserFactory.create(is_active=False, db=db_session)

    response = await client.post("/api/v1/auth/login", json={
        "email": inactive_staff.email,
        "password": "Test1234!"
    })

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"
```

---

### TC-AUTH-005: 有効なリフレッシュトークンで再発行

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_refresh_token_issues_new_access_token(client, db_session):
    doctor = await StaffUserFactory.create(db=db_session)
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": doctor.email, "password": "Test1234!"
    })
    old_token = login_resp.json()["data"]["access_token"]

    # 1秒待機してトークンが変わることを確認
    await asyncio.sleep(1)

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    new_token = response.json()["data"]["access_token"]
    # 新しいアクセストークンが発行されている
    assert new_token != old_token
    # トークンローテーション: Cookieも更新されている
    assert "refresh_token" in response.cookies
```

---

### TC-AUTH-006: 期限切れリフレッシュトークンの拒否

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_expired_refresh_token_is_rejected(client, db_session):
    # 有効期限を過去に設定したリフレッシュトークンを直接DBに作成
    doctor = await StaffUserFactory.create(db=db_session)
    expired_token = "expired-token-value"
    await RefreshTokenFactory.create(
        staff_user_id=doctor.id,
        token_hash=sha256(expired_token),
        expires_at=datetime.utcnow() - timedelta(hours=1),  # 1時間前に期限切れ
        db=db_session
    )
    client.cookies.set("refresh_token", expired_token)

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "REFRESH_TOKEN_EXPIRED"
```

---

### TC-AUTH-007: 再利用攻撃（リフレッシュトークンの二重使用）

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_reused_refresh_token_is_revoked(client, db_session):
    """同一リフレッシュトークンを2回使用すると検出・無効化される"""
    doctor = await StaffUserFactory.create(db=db_session)
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": doctor.email, "password": "Test1234!"
    })
    refresh_cookie = login_resp.cookies.get("refresh_token")

    # 1回目: 成功
    client.cookies.set("refresh_token", refresh_cookie)
    first_resp = await client.post("/api/v1/auth/refresh")
    assert first_resp.status_code == 200

    # 2回目: 同じ旧トークンで再試行 → 失効検出
    client.cookies.set("refresh_token", refresh_cookie)
    second_resp = await client.post("/api/v1/auth/refresh")
    assert second_resp.status_code == 401
    assert second_resp.json()["error"]["code"] == "REFRESH_TOKEN_REVOKED"
```

---

### TC-AUTH-008: ログアウトでCookieが削除される

| 優先度 | 中 | 種別 | 統合テスト |

```python
async def test_logout_clears_refresh_token_cookie(doctor_client):
    response = await doctor_client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    # Set-Cookie でMax-Age=0 または Expires=過去日時が設定されること
    set_cookie = response.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()
```

---

### TC-AUTH-009: メール形式バリデーション

| 優先度 | 中 | 種別 | 統合テスト |

```python
@pytest.mark.parametrize("invalid_email", [
    "not-an-email",
    "missing@",
    "@missing-local.com",
    "",
    "a" * 255 + "@example.com",  # 255文字超
])
async def test_login_rejects_invalid_email_format(client, invalid_email):
    response = await client.post("/api/v1/auth/login", json={
        "email": invalid_email,
        "password": "Test1234!"
    })
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
```

---

## 6. 患者向けAPIテスト (PAT)

### TC-PAT-001: QRトークン検証成功

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_valid_qr_token_returns_session_info(client, db_session):
    session = await InquirySessionFactory.create(
        status="pending",
        qr_expires_at=datetime.utcnow() + timedelta(hours=12),
        db=db_session
    )

    response = await client.get(f"/api/v1/sessions/{session.qr_token}/info")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"] == str(session.id)
    assert data["department_code"] is not None
    assert data["appointment_at"] is not None
    # 患者氏名が復号されて返ること（暗号化バイト列ではない）
    assert isinstance(data["patient_name"], str)
    assert len(data["patient_name"]) > 0
```

---

### TC-PAT-002: 有効期限切れQRトークン

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_expired_qr_token_returns_422(client, db_session):
    session = await InquirySessionFactory.create(
        status="pending",
        qr_expires_at=datetime.utcnow() - timedelta(minutes=1),  # 1分前に期限切れ
        db=db_session
    )

    response = await client.get(f"/api/v1/sessions/{session.qr_token}/info")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"
```

---

### TC-PAT-003: 使用済みQRトークン（問診完了済み）

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_completed_session_token_returns_422(client, db_session):
    session = await InquirySessionFactory.create(
        status="completed",
        db=db_session
    )

    response = await client.get(f"/api/v1/sessions/{session.qr_token}/info")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ALREADY_COMPLETED"
```

---

### TC-PAT-004: 存在しないQRトークン

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_nonexistent_token_returns_404(client):
    fake_token = str(uuid4())

    response = await client.get(f"/api/v1/sessions/{fake_token}/info")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
```

---

### TC-PAT-005: 問診フォーム定義取得

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_get_form_definition_returns_published_schema(client, db_session):
    session = await InquirySessionFactory.create(status="in_progress", db=db_session)
    form = await FormDefinitionFactory.create(
        department_id=session.department_id,
        status="published",
        db=db_session
    )

    response = await client.get(
        f"/api/v1/departments/{session.department.code}/form",
        params={"session_id": str(session.id)}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["form_definition_id"] == str(form.id)
    assert data["status"] == "published"  # ドラフトは返さない
    # スキーマの基本構造を確認
    assert "sections" in data["schema"]
    assert len(data["schema"]["sections"]) > 0
    # 各質問にIDとラベルがあること
    for section in data["schema"]["sections"]:
        for question in section["questions"]:
            assert "id" in question
            assert "label" in question
            assert "type" in question
```

---

### TC-PAT-006: ドラフトフォームは患者に返さない

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_draft_form_not_returned_to_patient(client, db_session):
    """公開中フォームなし（ドラフトのみ）の場合は422"""
    dept = await DepartmentFactory.create(db=db_session)
    session = await InquirySessionFactory.create(department_id=dept.id, db=db_session)
    await FormDefinitionFactory.create(
        department_id=dept.id,
        status="draft",  # ドラフトのみ
        db=db_session
    )

    response = await client.get(
        f"/api/v1/departments/{dept.code}/form",
        params={"session_id": str(session.id)}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_PUBLISHED_FORM"
```

---

### TC-PAT-007: 問診回答送信 - 正常系

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_submit_response_success(client, db_session):
    session = await InquirySessionFactory.create(status="in_progress", db=db_session)
    form = await FormDefinitionFactory.create(
        department_id=session.department_id, status="published", db=db_session
    )

    response = await client.post(
        f"/api/v1/sessions/{session.id}/responses",
        json={
            "form_definition_id": str(form.id),
            "common_answers": {
                "q_chief_complaint": "3日前から発熱と咳が続いています",
                "q_onset": "few_days",
                "q_severity": 6,
                "q_past_illness": ["hypertension"],
                "q_drug_allergy": False,
                "q_food_allergy": False,
                "q_current_medication": False,
                "q_smoking": "never",
                "q_alcohol": "occasional",
                "q_exercise": "few_times_week",
                "q_insurance_type": "shakai_hoken",
                "q_consent_privacy": True,
                "q_consent_ai": True,
            },
            "department_answers": {
                "q_fever": "yes",
                "q_max_temp": 38.5,
            }
        }
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert "response_id" in data
    assert data["ai_status"] == "pending"
    assert data["fhir_sync_status"] == "pending"

    # DBに回答が保存されていること（暗号化済みで保存）
    await db_session.refresh(session)
    assert session.status == "completed"
    response_record = await db_session.get(InquiryResponse, data["response_id"])
    assert response_record is not None
    assert response_record.answers_encrypted is not None  # 暗号化されている
    assert response_record.answers_iv is not None
```

---

### TC-PAT-008: 個人情報同意なしは送信不可、AI同意なしはスキップ

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_response_rejected_without_privacy_consent(client, db_session):
    """個人情報同意なしは送信不可（CONSENT_REQUIRED）"""
    session = await InquirySessionFactory.create(status="in_progress", db=db_session)
    answers = {**valid_common_answers(), "q_consent_privacy": False, "q_consent_ai": True}

    response = await client.post(
        f"/api/v1/sessions/{session.id}/responses",
        json={"form_definition_id": "...", "common_answers": answers, "department_answers": {}}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONSENT_REQUIRED"


async def test_response_without_ai_consent_skips_ai_analysis(client, db_session):
    """AI利用同意なし（q_consent_ai: false）でも送信可能。ai_status='skipped'になる"""
    session = await InquirySessionFactory.create(status="in_progress", db=db_session)
    answers = {**valid_common_answers(), "q_consent_privacy": True, "q_consent_ai": False}

    response = await client.post(
        f"/api/v1/sessions/{session.id}/responses",
        json={"form_definition_id": "...", "common_answers": answers, "department_answers": {}}
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["ai_status"] == "skipped"       # AI分析がスキップされること
    assert data["fhir_sync_status"] == "pending"  # FHIR同期は実行されること
```

---

### TC-PAT-009: 重複送信の防止

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_duplicate_response_submission_returns_409(client, db_session):
    session = await InquirySessionFactory.create(status="completed", db=db_session)
    await InquiryResponseFactory.create(session_id=session.id, db=db_session)

    response = await client.post(
        f"/api/v1/sessions/{session.id}/responses",
        json=valid_response_payload(session)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESPONSE_ALREADY_EXISTS"
```

---

### TC-PAT-010: 体温の境界値バリデーション

| 優先度 | 中 | 種別 | 統合テスト |

```python
@pytest.mark.parametrize("temp,expected_status", [
    (35.0, 201),   # 最小値（OK）
    (42.0, 201),   # 最大値（OK）
    (34.9, 400),   # 最小値未満
    (42.1, 400),   # 最大値超過
    (-1.0, 400),   # 負の値
])
async def test_body_temperature_boundary_validation(client, db_session, temp, expected_status):
    session = await InquirySessionFactory.create(status="in_progress", db=db_session)
    payload = valid_response_payload(session)
    payload["department_answers"]["q_max_temp"] = temp

    response = await client.post(f"/api/v1/sessions/{session.id}/responses", json=payload)

    assert response.status_code == expected_status
```

---

## 7. 受付スタッフAPIテスト (REC)

### TC-REC-001: QRコード発行成功

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_create_session_returns_qr_token(reception_client, db_session):
    dept = await DepartmentFactory.create(db=db_session)
    await FormDefinitionFactory.create(department_id=dept.id, status="published", db=db_session)
    doctor = await StaffUserFactory.create(role="doctor", department_ids=[dept.id], db=db_session)
    patient = await PatientFactory.create(db=db_session)

    response = await reception_client.post("/api/v1/sessions", json={
        "external_patient_id": patient.external_patient_id,
        "department_id": str(dept.id),
        "appointment_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "doctor_id": str(doctor.id)
    })

    assert response.status_code == 201
    data = response.json()["data"]
    assert "qr_token" in data
    assert "qr_image_url" in data
    assert "qr_url" in data
    assert data["status"] == "pending"
    assert data["doctor_name"] == doctor.full_name  # 担当医名が返ること
    # QRトークンがUUID形式であること
    uuid.UUID(data["qr_token"])  # 無効なUUIDなら ValueError が出る
    # QR有効期限が予約日翌日以降であること
    expires_at = datetime.fromisoformat(data["qr_expires_at"])
    appointment_at = datetime.fromisoformat(data["appointment_at"])
    assert expires_at > appointment_at
```

---

### TC-REC-002: 公開中フォームなしでのQR発行拒否

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_create_session_fails_without_published_form(reception_client, db_session):
    dept = await DepartmentFactory.create(db=db_session)
    # フォームを作成しない（または draft のみ）

    response = await reception_client.post("/api/v1/sessions", json={
        "external_patient_id": "000001",
        "department_id": str(dept.id),
        "appointment_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    })

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_PUBLISHED_FORM"
```

---

### TC-REC-003: 同一患者・科・日時での重複発行防止

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_duplicate_session_creation_returns_409(reception_client, db_session):
    session = await InquirySessionFactory.create(status="pending", db=db_session)

    # 同じ患者・科・日時で再作成を試みる
    response = await reception_client.post("/api/v1/sessions", json={
        "external_patient_id": session.patient.external_patient_id,
        "department_id": str(session.department_id),
        "appointment_at": session.appointment_at.isoformat()
    })

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SESSION_ALREADY_EXISTS"
```

---

### TC-REC-004: セッションキャンセル

| 優先度 | 高 | 種別 | 統合テスト |

```python
@pytest.mark.parametrize("initial_status", ["pending", "in_progress"])
async def test_cancel_session_success(reception_client, db_session, initial_status):
    session = await InquirySessionFactory.create(status=initial_status, db=db_session)

    response = await reception_client.patch(
        f"/api/v1/sessions/{session.id}",
        json={"status": "cancelled"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cancelled"
    await db_session.refresh(session)
    assert session.status == "cancelled"
```

---

### TC-REC-005: 完了済みセッションはキャンセル不可

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_cannot_cancel_completed_session(reception_client, db_session):
    session = await InquirySessionFactory.create(status="completed", db=db_session)

    response = await reception_client.patch(
        f"/api/v1/sessions/{session.id}",
        json={"status": "cancelled"}
    )

    assert response.status_code == 409
```

---

### TC-REC-006: nurseロールは一覧のみ・キャンセル不可

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_nurse_can_list_sessions_but_not_cancel(nurse_client, db_session):
    session = await InquirySessionFactory.create(status="pending", db=db_session)

    # 一覧は取得できる
    list_resp = await nurse_client.get("/api/v1/sessions")
    assert list_resp.status_code == 200

    # キャンセルはできない
    cancel_resp = await nurse_client.patch(
        f"/api/v1/sessions/{session.id}",
        json={"status": "cancelled"}
    )
    assert cancel_resp.status_code == 403
    assert cancel_resp.json()["error"]["code"] == "PERMISSION_DENIED"
```

---

### TC-REC-007: 過去日時でのQR発行拒否

| 優先度 | 中 | 種別 | 統合テスト |

```python
async def test_create_session_rejects_past_appointment(reception_client, db_session):
    dept = await DepartmentFactory.create(db=db_session)
    await FormDefinitionFactory.create(department_id=dept.id, status="published", db=db_session)

    response = await reception_client.post("/api/v1/sessions", json={
        "external_patient_id": "000001",
        "department_id": str(dept.id),
        "appointment_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()  # 過去
    })

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
```

---

### TC-REC-008: QRコード画像取得

| 優先度 | 中 | 種別 | 統合テスト |

```python
async def test_get_qr_image_returns_png(reception_client, db_session):
    session = await InquirySessionFactory.create(status="pending", db=db_session)

    response = await reception_client.get(f"/api/v1/sessions/{session.id}/qr.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    # PNG マジックバイト確認
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(response.content) > 100  # 空ファイルではない
```

---

## 8. 医師用ダッシュボードAPIテスト (DASH)

### TC-DASH-001: 担当外診療科の患者詳細は閲覧不可

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_doctor_cannot_view_other_departments_patient(db_session, client):
    naika_dept = await DepartmentFactory.create(code="naika", db=db_session)
    geka_dept = await DepartmentFactory.create(code="geka", db=db_session)

    # 内科担当の医師
    doctor = await StaffUserFactory.create(
        role="doctor",
        department_ids=[naika_dept.id],
        db=db_session
    )
    # 外科の患者セッション
    session = await InquirySessionFactory.create(
        department_id=geka_dept.id,
        status="completed",
        db=db_session
    )
    await InquiryResponseFactory.create(session_id=session.id, db=db_session)

    token = login_as(doctor)
    client.headers["Authorization"] = f"Bearer {token}"
    response = await client.get(f"/api/v1/dashboard/sessions/{session.id}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
```

---

### TC-DASH-002: AIサマリー生成中はprocessingステータスで返る

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_dashboard_session_returns_processing_ai_status(doctor_client, db_session):
    session = await InquirySessionFactory.create(status="completed", db=db_session)
    await InquiryResponseFactory.create(
        session_id=session.id,
        ai_status="processing",
        ai_summary_encrypted=None,  # まだ生成されていない
        db=db_session
    )

    response = await doctor_client.get(f"/api/v1/dashboard/sessions/{session.id}")

    assert response.status_code == 200
    ai_summary = response.json()["data"]["ai_summary"]
    assert ai_summary["status"] == "processing"
    assert ai_summary["symptom_summary"] is None
    assert ai_summary["risk_flags"] == []
```

---

### TC-DASH-003: 要注意フラグ付き患者が一覧上位に表示

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_patients_with_risk_flags_appear_first_in_dashboard(doctor_client, db_session):
    dept = await DepartmentFactory.create(db=db_session)
    # フラグなし患者（9:00予約）
    session_no_flag = await InquirySessionFactory.create(
        department_id=dept.id,
        appointment_at=datetime.utcnow().replace(hour=9, minute=0),
        status="completed", db=db_session
    )
    await InquiryResponseFactory.create(
        session_id=session_no_flag.id, ai_status="completed",
        ai_summary={"risk_flags": []}, db=db_session
    )
    # フラグあり患者（10:00予約 = 後から）
    session_with_flag = await InquirySessionFactory.create(
        department_id=dept.id,
        appointment_at=datetime.utcnow().replace(hour=10, minute=0),
        status="completed", db=db_session
    )
    await InquiryResponseFactory.create(
        session_id=session_with_flag.id, ai_status="completed",
        ai_summary={"risk_flags": [{"type": "drug_allergy", "severity": "high"}]},
        db=db_session
    )

    response = await doctor_client.get("/api/v1/dashboard/sessions")

    assert response.status_code == 200
    patients = response.json()["data"]
    # フラグありが先頭に来る
    assert patients[0]["session_id"] == str(session_with_flag.id)
    assert patients[0]["has_risk_flags"] is True
    assert patients[1]["has_risk_flags"] is False
```

---

### TC-DASH-004: 過去問診履歴の時系列順

| 優先度 | 中 | 種別 | 統合テスト |

```python
async def test_patient_history_is_ordered_by_date_descending(doctor_client, db_session):
    patient = await PatientFactory.create(db=db_session)
    sessions = [
        await InquirySessionFactory.create(
            patient_id=patient.id,
            appointment_at=datetime(2026, 1, i, 10, 0),
            status="completed", db=db_session
        )
        for i in range(1, 6)  # 1月1日〜5日
    ]

    response = await doctor_client.get(f"/api/v1/patients/{patient.id}/sessions")

    assert response.status_code == 200
    history = response.json()["data"]
    # 最新日（1月5日）が先頭
    dates = [item["appointment_at"] for item in history]
    assert dates == sorted(dates, reverse=True)
```

---

### TC-DASH-005: PDF出力に患者情報が含まれる

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_pdf_output_contains_required_fields(doctor_client, db_session):
    session = await InquirySessionFactory.create(status="completed", db=db_session)
    await InquiryResponseFactory.create(
        session_id=session.id, ai_status="completed", db=db_session
    )

    response = await doctor_client.get(f"/api/v1/responses/{session.response.id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    # PDFマジックバイト
    assert response.content[:4] == b"%PDF"
    assert len(response.content) > 1000  # 空PDFではない
    # Content-Disposition ヘッダーがあること
    assert "attachment" in response.headers.get("content-disposition", "")
```

---

## 9. 管理者APIテスト (ADM)

### TC-ADM-001: フォーム公開でバージョンが更新される

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_publishing_form_archives_previous_version(admin_client, db_session):
    dept = await DepartmentFactory.create(db=db_session)
    old_form = await FormDefinitionFactory.create(
        department_id=dept.id, status="published", version=1, db=db_session
    )
    new_form = await FormDefinitionFactory.create(
        department_id=dept.id, status="draft", version=2, db=db_session
    )

    response = await admin_client.post(f"/api/v1/admin/forms/{new_form.id}/publish")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "published"
    assert response.json()["data"]["archived_form_id"] == str(old_form.id)

    # 旧フォームがアーカイブされていること
    await db_session.refresh(old_form)
    assert old_form.status == "archived"
    # 新フォームが公開されていること
    await db_session.refresh(new_form)
    assert new_form.status == "published"
```

---

### TC-ADM-002: 公開済みフォームの直接更新は拒否

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_cannot_update_published_form_directly(admin_client, db_session):
    form = await FormDefinitionFactory.create(status="published", db=db_session)

    response = await admin_client.put(
        f"/api/v1/admin/forms/{form.id}",
        json={"schema": {"title": "変更後", "sections": []}}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FORM_NOT_DRAFT"
```

---

### TC-ADM-003: フォーム複製でバージョン番号が採番される

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_duplicate_form_assigns_next_version_number(admin_client, db_session):
    dept = await DepartmentFactory.create(db=db_session)
    form_v3 = await FormDefinitionFactory.create(
        department_id=dept.id, status="published", version=3, db=db_session
    )

    response = await admin_client.post(f"/api/v1/admin/forms/{form_v3.id}/duplicate")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["version"] == 4  # 次のバージョン番号
    assert data["status"] == "draft"
    assert data["copied_from_version"] == 3
```

---

### TC-ADM-004: 自分自身を無効化できない

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_admin_cannot_deactivate_themselves(admin_client, db_session, current_admin):
    response = await admin_client.patch(
        f"/api/v1/admin/staff/{current_admin.id}/status",
        json={"is_active": False}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SELF_DEACTIVATION"
```

---

### TC-ADM-005: 最後のadminは無効化できない

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_cannot_deactivate_last_admin(db_session, client):
    """adminが1人しかいない場合は無効化不可"""
    # 既存adminを全員確認し、1人だけ残す状態を作る
    only_admin = await StaffUserFactory.create(role="admin", db=db_session)
    # only_adminとしてログイン
    token = login_as(only_admin)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.patch(
        f"/api/v1/admin/staff/{only_admin.id}/status",
        json={"is_active": False}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] in (
        "SELF_DEACTIVATION", "LAST_ADMIN_DEACTIVATION"
    )
```

---

### TC-ADM-006: 監査ログが90日を超える範囲指定で拒否

| 優先度 | 中 | 種別 | 統合テスト |

```python
async def test_audit_log_rejects_range_over_90_days(admin_client):
    response = await admin_client.get("/api/v1/admin/audit-logs", params={
        "from": "2025-01-01",
        "to": "2025-12-31"  # 364日（90日超）
    })

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
```

---

### TC-ADM-007: adminロールがないと管理APIにアクセス不可

| 優先度 | 高 | 種別 | 統合テスト |

```python
@pytest.mark.parametrize("role", ["doctor", "nurse", "reception"])
async def test_non_admin_cannot_access_admin_endpoints(client, db_session, role):
    staff = await StaffUserFactory.create(role=role, db=db_session)
    token = login_as(staff)
    client.headers["Authorization"] = f"Bearer {token}"

    admin_endpoints = [
        ("GET", "/api/v1/admin/forms"),
        ("GET", "/api/v1/admin/staff"),
        ("GET", "/api/v1/admin/audit-logs", {"from": "2026-01-01", "to": "2026-01-02"}),
        ("GET", "/api/v1/admin/settings"),
    ]

    for method, path, *params in admin_endpoints:
        resp = await client.request(method, path, params=params[0] if params else {})
        assert resp.status_code == 403, f"Expected 403 for {method} {path} as {role}"
        assert resp.json()["error"]["code"] == "PERMISSION_DENIED"
```

---

## 10. サービス層テスト (SVC)

### TC-SVC-001: 暗号化・復号の一貫性

| 優先度 | 高 | 種別 | 単体テスト |

```python
def test_encrypt_decrypt_roundtrip():
    """暗号化→復号で元のデータに戻ること"""
    from app.core.security import encrypt_field, decrypt_field

    original_text = "田中 花子"
    encrypted, iv = encrypt_field(original_text)

    assert encrypted != original_text.encode()  # 暗号化されていること
    assert len(iv) == 12  # GCM IV は12バイト

    decrypted = decrypt_field(encrypted, iv)
    assert decrypted == original_text
```

---

### TC-SVC-002: 同一平文でも毎回異なる暗号文（IV再利用禁止）

| 優先度 | 高 | 種別 | 単体テスト |

```python
def test_each_encryption_uses_unique_iv():
    """同じ平文でも暗号化のたびに異なるIVが生成される"""
    from app.core.security import encrypt_field

    text = "田中 花子"
    results = [encrypt_field(text) for _ in range(100)]
    ivs = [iv for _, iv in results]
    encrypted_values = [enc for enc, _ in results]

    # IVが全て異なること（確率的にほぼ確実）
    assert len(set(ivs)) == 100
    # 暗号文も全て異なること
    assert len(set(encrypted_values)) == 100
```

---

### TC-SVC-003: 改ざんデータの復号失敗

| 優先度 | 高 | 種別 | 単体テスト |

```python
def test_tampered_ciphertext_raises_error():
    """GCM認証タグ検証により改ざんを検出する"""
    from app.core.security import encrypt_field, decrypt_field

    encrypted, iv = encrypt_field("田中 花子")
    # 暗号文の最後のバイトを1ビット反転（改ざん）
    tampered = encrypted[:-1] + bytes([encrypted[-1] ^ 0x01])

    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_field(tampered, iv)
```

---

### TC-SVC-004: QRコード生成の検証

| 優先度 | 中 | 種別 | 単体テスト |

```python
def test_qr_code_generates_valid_png():
    """QRコードがPNG形式で生成され、埋め込みURLが読み取れること"""
    import qrcode
    from app.services.qr_service import generate_qr_code
    from pyzbar.pyzbar import decode
    from PIL import Image
    import io

    token = str(uuid4())
    png_bytes = generate_qr_code(token, base_url="https://inquiry.hospital.example.com")

    # PNGマジックバイト確認
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    # QRコードの内容を読み取り
    img = Image.open(io.BytesIO(png_bytes))
    decoded = decode(img)
    assert len(decoded) == 1
    qr_url = decoded[0].data.decode()
    assert token in qr_url
    assert "https://inquiry.hospital.example.com" in qr_url
```

---

### TC-SVC-005: AIプロンプトに個人識別情報が含まれない

| 優先度 | 高 | 種別 | 単体テスト |

```python
async def test_ai_prompt_excludes_personal_identifiers():
    """Claude APIに送るプロンプトに氏名・生年月日が含まれないこと"""
    from app.services.ai_analysis import build_ai_prompt

    answers = {
        "q_chief_complaint": "発熱と咳",
        "q_drug_allergy_detail": "ペニシリン系",
    }
    patient_info = {
        "name": "田中 花子",       # 氏名
        "dob": "1975-08-15",       # 生年月日
        "phone": "090-XXXX-XXXX",  # 電話番号
    }

    prompt = build_ai_prompt(answers=answers, patient_info=patient_info)

    # 個人識別情報がプロンプトに含まれていないこと
    assert "田中" not in prompt
    assert "花子" not in prompt
    assert "1975-08-15" not in prompt
    assert "090" not in prompt
    # 症状情報は含まれること
    assert "発熱" in prompt
    assert "ペニシリン" in prompt
```

---

### TC-SVC-006: AIサマリー失敗時のフォールバック

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_ai_analysis_failure_sets_failed_status(db_session, respx_mock):
    """Claude APIが失敗してもシステムが落ちず、failedステータスで記録される"""
    from app.services.ai_analysis import analyze_and_save_summary

    respx_mock.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(500, json={"error": "Internal server error"})
    )
    response_record = await InquiryResponseFactory.create(
        ai_status="processing", db=db_session
    )

    await analyze_and_save_summary(response_id=str(response_record.id))

    await db_session.refresh(response_record)
    assert response_record.ai_status == "failed"
    assert response_record.ai_summary_encrypted is None  # サマリーなし
```

---

### TC-SVC-007: FHIR送信リトライ（指数バックオフ）

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_fhir_sync_retries_on_failure(db_session, respx_mock):
    """FHIR送信失敗時にリトライキューが更新される"""
    from app.services.fhir_client import sync_to_fhir

    # 1回目: 503エラー
    respx_mock.post("http://localhost:9999/fhir/R4/QuestionnaireResponse").mock(
        return_value=httpx.Response(503)
    )

    queue_entry = await FhirSyncQueueFactory.create(retry_count=0, db=db_session)
    await sync_to_fhir(queue_id=str(queue_entry.id))

    await db_session.refresh(queue_entry)
    assert queue_entry.retry_count == 1
    assert queue_entry.status == "pending"
    # next_retry_at が now + 1分以上であること（FHIRキューの1回目リトライは+1分）
    assert queue_entry.next_retry_at > datetime.utcnow() + timedelta(seconds=55)

async def test_fhir_sync_fails_permanently_after_3_retries(db_session, respx_mock):
    """3回全て失敗するとfailed確定になる"""
    respx_mock.post("http://localhost:9999/fhir/R4/QuestionnaireResponse").mock(
        return_value=httpx.Response(503)
    )
    queue_entry = await FhirSyncQueueFactory.create(retry_count=3, db=db_session)

    await sync_to_fhir(queue_id=str(queue_entry.id))

    await db_session.refresh(queue_entry)
    assert queue_entry.status == "failed"
    assert queue_entry.retry_count == 3  # 上限で止まる
```

---

### TC-SVC-008: 監査ログの自動記録

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_reading_patient_data_is_logged_in_audit(doctor_client, db_session):
    """医師が患者詳細を閲覧すると監査ログに記録される"""
    session = await InquirySessionFactory.create(status="completed", db=db_session)
    await InquiryResponseFactory.create(session_id=session.id, db=db_session)

    await doctor_client.get(f"/api/v1/dashboard/sessions/{session.id}")

    # 監査ログが作成されていること
    log = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.resource_type == "inquiry_response")
        .where(AuditLog.action == "read")
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    log_entry = log.scalar_one_or_none()
    assert log_entry is not None
    assert str(session.id) in (log_entry.resource_id or "")
```

---

## 11. セキュリティテスト (SEC)

### TC-SEC-001: JWT認証なしはすべて401

| 優先度 | 高 | 種別 | 統合テスト |

```python
@pytest.mark.parametrize("method,path", [
    ("GET",  "/api/v1/sessions"),
    ("GET",  "/api/v1/dashboard/sessions"),
    ("GET",  "/api/v1/admin/forms"),
    ("GET",  "/api/v1/admin/staff"),
    ("GET",  "/api/v1/departments"),
])
async def test_unauthenticated_requests_return_401(client, method, path):
    response = await client.request(method, path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"
```

---

### TC-SEC-002: 改ざんJWTは拒否

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_tampered_jwt_is_rejected(client):
    # 正規トークンの署名部分を変更
    valid_token = "eyJ...valid_header.valid_payload.valid_signature"
    tampered_token = valid_token[:-5] + "XXXXX"

    client.headers["Authorization"] = f"Bearer {tampered_token}"
    response = await client.get("/api/v1/dashboard/sessions")

    assert response.status_code == 401
```

---

### TC-SEC-003: SQLインジェクション対策

| 優先度 | 高 | 種別 | 統合テスト |

```python
@pytest.mark.parametrize("injection_payload", [
    "'; DROP TABLE patients; --",
    "1 OR 1=1",
    "admin'--",
    "1; SELECT * FROM staff_users",
])
async def test_sql_injection_in_search_params(reception_client, injection_payload):
    """検索パラメータへのSQLインジェクション試行は無害化される"""
    response = await reception_client.get(
        "/api/v1/sessions",
        params={"search": injection_payload}
    )

    # エラーになるかもしれないが500ではないこと
    assert response.status_code in (200, 400)
    assert response.status_code != 500
    # テーブルが生きていること（削除されていない）
    patients_check = await reception_client.get("/api/v1/sessions")
    assert patients_check.status_code != 500
```

---

### TC-SEC-004: 患者データがDB上で暗号化されていること

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_patient_data_is_encrypted_at_rest(db_session):
    """DBに直接アクセスしても氏名が平文で見えないこと"""
    patient = await PatientFactory.create(db=db_session, name="田中 花子")

    # ORMを通さず生のSQLで確認
    result = await db_session.execute(
        text("SELECT name_encrypted FROM patients WHERE id = :id"),
        {"id": patient.id}
    )
    raw_data = result.scalar()

    assert raw_data is not None
    # バイト列で保存されていること
    assert isinstance(raw_data, (bytes, memoryview))
    # 平文が含まれていないこと
    assert b"\xe7\x94\xb0\xe4\xb8\xad" not in raw_data  # "田中" のUTF-8
```

---

### TC-SEC-005: XSS対策（レスポンスのContent-Type）

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_api_responses_have_correct_content_type(client, db_session):
    """APIレスポンスがapplication/jsonであること（XSS対策）"""
    doctor = await StaffUserFactory.create(role="doctor", db=db_session)
    response = await client.post("/api/v1/auth/login", json={
        "email": doctor.email, "password": "Test1234!"
    })

    content_type = response.headers.get("content-type", "")
    assert "application/json" in content_type
    assert "text/html" not in content_type
```

---

### TC-SEC-006: レート制限の動作確認

| 優先度 | 高 | 種別 | 統合テスト |

```python
async def test_rate_limit_on_login_endpoint(client):
    """ログインエンドポイントは10req/分を超えると429"""
    responses = []
    for _ in range(15):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@test.com", "password": "wrong"
        })
        responses.append(resp.status_code)

    # 10回を超えた時点で429が返ること
    assert 429 in responses
    # 429レスポンスにRetry-Afterヘッダーがあること
    last_429 = next(r for r in responses if r == 429)  # 最初の429
    # ... Retry-After ヘッダー確認
```

---

### TC-SEC-007: CORS設定の検証

| 優先度 | 中 | 種別 | 統合テスト |

```python
async def test_cors_rejects_unauthorized_origin(client):
    """許可されていないオリジンからのリクエストはCORSで拒否される"""
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        }
    )

    # Access-Control-Allow-Origin に evil.example.com は含まれない
    allow_origin = response.headers.get("access-control-allow-origin", "")
    assert "evil.example.com" not in allow_origin
```

---

### TC-SEC-008: 監査ログの改ざん不可

| 優先度 | 高 | 種別 | 単体テスト（DB）|

```python
async def test_audit_log_cannot_be_updated_or_deleted(db_session):
    """監査ログはINSERT ONLYポリシーによりUPDATE/DELETEが失敗する"""
    log = await AuditLogFactory.create(db=db_session)

    # UPDATE試行
    with pytest.raises(Exception):  # PGの RLS エラー
        await db_session.execute(
            text("UPDATE audit_logs SET action = 'delete' WHERE id = :id"),
            {"id": log.id}
        )

    # DELETE試行
    with pytest.raises(Exception):
        await db_session.execute(
            text("DELETE FROM audit_logs WHERE id = :id"),
            {"id": log.id}
        )
```

---

## 12. フロントエンドテスト (FE)

### TC-FE-001: 問診フォームの動的分岐が正しく動作する

| 優先度 | 高 | 種別 | コンポーネントテスト |

```typescript
// frontend/src/components/form-engine/BranchEngine.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuestionRenderer } from "./QuestionRenderer";

test("発熱「はい」選択で追加質問が展開される", async () => {
  const user = userEvent.setup();
  const schema = {
    id: "q_fever",
    type: "radio",
    label: "発熱はありますか？",
    options: [
      { value: "yes", label: "はい" },
      { value: "no", label: "いいえ" },
    ],
    branches: [{
      condition: { operator: "eq", value: "yes" },
      show_question_ids: ["q_max_temp"],
    }],
  };
  const allQuestions = [
    schema,
    { id: "q_max_temp", type: "number", label: "最高体温（℃）", visible_by_default: false },
  ];

  render(<QuestionRenderer questions={allQuestions} onChange={vi.fn()} />);

  // 初期状態: 追加質問は非表示
  expect(screen.queryByLabelText("最高体温（℃）")).not.toBeInTheDocument();

  // 「はい」を選択
  await user.click(screen.getByLabelText("はい"));

  // 追加質問が展開される
  expect(screen.getByLabelText("最高体温（℃）")).toBeInTheDocument();
});

test("発熱「はい」→「いいえ」変更で追加質問が折り畳まれ、入力値がリセットされる", async () => {
  const user = userEvent.setup();
  // ... （上記と同様のセットアップ）

  await user.click(screen.getByLabelText("はい"));
  const tempInput = screen.getByLabelText("最高体温（℃）");
  await user.type(tempInput, "38.5");

  await user.click(screen.getByLabelText("いいえ"));

  // 折り畳まれること
  expect(screen.queryByLabelText("最高体温（℃）")).not.toBeInTheDocument();

  // 「はい」に戻したとき値がリセットされていること
  await user.click(screen.getByLabelText("はい"));
  expect(screen.getByLabelText("最高体温（℃）")).toHaveValue(null);
});
```

---

### TC-FE-002: LocalStorageへの自動保存

| 優先度 | 高 | 種別 | コンポーネントテスト |

```typescript
test("回答入力のたびにLocalStorageに保存される", async () => {
  const user = userEvent.setup();
  render(<InquiryForm sessionId="test-session-id" />);

  const textarea = screen.getByLabelText("今日の受診理由を教えてください");
  await user.type(textarea, "発熱と咳");

  const saved = JSON.parse(localStorage.getItem("inquiry_test-session-id") ?? "{}");
  expect(saved.q_chief_complaint).toBe("発熱と咳");
});

test("ページリロード後も保存データが復元される", () => {
  localStorage.setItem("inquiry_test-session-id", JSON.stringify({
    q_chief_complaint: "発熱と咳"
  }));

  render(<InquiryForm sessionId="test-session-id" />);

  const textarea = screen.getByLabelText("今日の受診理由を教えてください");
  expect(textarea).toHaveValue("発熱と咳");
});
```

---

### TC-FE-003: 同意なしは送信ボタンが無効

| 優先度 | 高 | 種別 | コンポーネントテスト |

```typescript
test("同意チェックがないと送信ボタンが無効化される", async () => {
  const user = userEvent.setup();
  render(<ConfirmScreen />);

  const submitButton = screen.getByRole("button", { name: "この内容で送信する" });

  // 初期状態: 無効
  expect(submitButton).toBeDisabled();

  // 一方の同意のみでは有効にならない
  await user.click(screen.getByLabelText("個人情報の取り扱いに同意する"));
  expect(submitButton).toBeDisabled();

  // 両方チェックで有効
  await user.click(screen.getByLabelText("AI分析への利用に同意する"));
  expect(submitButton).toBeEnabled();
});
```

---

### TC-FE-004: AIサマリーのポーリング

| 優先度 | 高 | 種別 | コンポーネントテスト |

```typescript
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

test("AIサマリーがprocessingの間ポーリングし完了後に表示する", async () => {
  let callCount = 0;

  server.use(
    http.get("/api/v1/dashboard/sessions/:id", () => {
      callCount++;
      if (callCount < 3) {
        return HttpResponse.json({
          data: { ai_summary: { status: "processing", symptom_summary: null } }
        });
      }
      return HttpResponse.json({
        data: { ai_summary: { status: "completed", symptom_summary: "発熱38.5℃と湿性咳" } }
      });
    })
  );

  render(<PatientDetailPage sessionId="test-id" />);

  // 初期: ローディング表示
  expect(screen.getByText("AI分析中...")).toBeInTheDocument();

  // 完了後: サマリーが表示される
  await screen.findByText("発熱38.5℃と湿性咳", {}, { timeout: 5000 });
  expect(screen.queryByText("AI分析中...")).not.toBeInTheDocument();
});
```

---

### TC-FE-005: 要注意フラグの視覚的強調

| 優先度 | 高 | 種別 | コンポーネントテスト |

```typescript
test("要注意フラグのある患者行に警告スタイルが適用される", () => {
  const patients = [
    { session_id: "1", patient_name: "田中 花子", has_risk_flags: true, risk_flags: [{ type: "drug_allergy", severity: "high" }] },
    { session_id: "2", patient_name: "佐藤 健", has_risk_flags: false, risk_flags: [] },
  ];

  render(<PatientTable patients={patients} />);

  const rows = screen.getAllByRole("row");
  // フラグありの行
  expect(rows[1]).toHaveClass("bg-red-50");  // 赤背景
  expect(within(rows[1]).getByText("⚠️")).toBeInTheDocument();
  // フラグなしの行
  expect(rows[2]).not.toHaveClass("bg-red-50");
});
```

---

## 13. E2Eテスト (E2E)

### TC-E2E-001: 患者の問診完了フロー

| 優先度 | 高 | 種別 | E2E (Playwright) |

```typescript
// frontend/tests/e2e/patient-inquiry.spec.ts
import { test, expect } from "@playwright/test";

test("患者がQRスキャンから問診完了まで正常に完了できる", async ({ page }) => {
  // テスト用セッションを事前にAPIで作成
  const sessionResp = await fetch("http://localhost:8000/api/v1/sessions", {
    method: "POST",
    headers: { "Authorization": `Bearer ${RECEPTION_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      external_patient_id: "999001",
      department_id: NAIKA_DEPT_ID,
      appointment_at: new Date(Date.now() + 3600000).toISOString(),
    }),
  });
  const { qr_token, session_id } = (await sessionResp.json()).data;

  // QRリンクを直接開く（QRスキャン相当）
  await page.goto(`http://localhost:3000/inquiry?token=${qr_token}`);

  // P-01: 問診開始画面
  await expect(page.getByText("問診票を記入する")).toBeVisible();
  await page.getByRole("button", { name: "問診票を記入する" }).click();

  // P-02: 共通フォーム - 主訴入力
  await page.getByLabel("今日の受診理由を教えてください").fill("3日前から発熱と咳が続いています");
  await page.getByLabel("数日前").check();
  await page.getByRole("radio", { name: "6" }).check();  // 症状程度
  await page.getByRole("button", { name: "次へ" }).click();

  // 既往歴・アレルギー
  await page.getByLabel("高血圧").check();
  await page.getByLabel("薬剤アレルギーあり").check();
  await page.getByLabel("薬品名（アレルギー）").fill("ペニシリン系");
  await page.getByRole("button", { name: "次へ" }).click();

  // 服薬
  await page.getByLabel("処方薬を服用中").check();
  await page.getByLabel("薬品名").fill("ワーファリン 2mg");
  await page.getByRole("button", { name: "次へ" }).click();

  // 生活習慣
  await page.getByLabel("喫煙なし").check();
  await page.getByLabel("飲酒: 機会飲酒").check();
  await page.getByRole("button", { name: "次へ" }).click();

  // 保険・同意
  await page.getByLabel("社会保険").check();
  await page.getByLabel("個人情報の取り扱いに同意する").check();
  await page.getByLabel("AI分析への利用に同意する").check();
  await page.getByRole("button", { name: "次へ" }).click();

  // P-03: 診療科別フォーム
  await page.getByLabel("発熱: はい").check();
  await expect(page.getByLabel("最高体温（℃）")).toBeVisible();  // 動的展開
  await page.getByLabel("最高体温（℃）").fill("38.5");
  await page.getByRole("button", { name: "確認画面へ" }).click();

  // P-04: 確認画面
  await expect(page.getByText("3日前から発熱と咳が続いています")).toBeVisible();
  await expect(page.getByText("ペニシリン系")).toBeVisible();
  await page.getByRole("button", { name: "この内容で送信する" }).click();

  // P-05: 完了画面
  await expect(page.getByText("問診票の送信が完了しました")).toBeVisible();
  await expect(page.getByText("受付窓口にお越しいただき")).toBeVisible();

  // URLが完了画面になっていること
  await expect(page).toHaveURL(/\/inquiry\/complete/);
});
```

---

### TC-E2E-002: 医師が患者詳細でAIサマリーを確認する

| 優先度 | 高 | 種別 | E2E (Playwright) |

```typescript
test("医師がダッシュボードから患者詳細・AIサマリーを確認できる", async ({ page }) => {
  await page.goto("http://localhost:3000/staff/login");
  await page.getByLabel("メールアドレス").fill("doctor@hospital.test");
  await page.getByLabel("パスワード").fill("Test1234!");
  await page.getByRole("button", { name: "ログイン" }).click();

  await expect(page).toHaveURL(/\/dashboard/);

  // 要注意フラグのある患者を選択
  const riskyPatient = page.locator("tr", { has: page.getByText("⚠️") }).first();
  await expect(riskyPatient).toBeVisible();
  await riskyPatient.click();

  await expect(page).toHaveURL(/\/dashboard\/patient\//);

  // 2カラムレイアウト
  await expect(page.getByText("問診回答")).toBeVisible();
  await expect(page.getByText("AIサマリー")).toBeVisible();

  // AIサマリーの免責文
  await expect(page.getByText("参考情報")).toBeVisible();

  // 要注意フラグの表示
  await expect(page.getByText("薬剤アレルギー")).toBeVisible();
});
```

---

### TC-E2E-003: 管理者がフォームを公開する

| 優先度 | 高 | 種別 | E2E (Playwright) |

```typescript
test("管理者がドラフトフォームを公開できる", async ({ page }) => {
  await loginAs(page, "admin@hospital.test");

  await page.goto("http://localhost:3000/admin/forms");
  await expect(page.getByText("フォーム管理")).toBeVisible();

  // ドラフトフォームの「編集」をクリック
  const draftRow = page.locator("tr", { has: page.getByText("ドラフト") }).first();
  await draftRow.getByRole("button", { name: "編集" }).click();

  await expect(page).toHaveURL(/\/admin\/forms\/.*\/edit/);

  // 公開ボタン
  await page.getByRole("button", { name: "公開する" }).click();

  // 確認モーダル
  await expect(page.getByText("フォームを公開しますか？")).toBeVisible();
  await page.getByRole("button", { name: "公開する" }).click();

  // 成功トースト
  await expect(page.getByText("フォームを公開しました")).toBeVisible();

  // 一覧に戻って公開済みになっていること
  await page.goto("http://localhost:3000/admin/forms");
  await expect(page.getByText("公開中")).toBeVisible();
});
```

---

## 14. 性能テスト (PERF)

### TC-PERF-001: 問診フォーム表示 - 2秒以内

| 優先度 | 高 | 種別 | 性能テスト (Locust) |

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class PatientUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # テスト用セッションを作成してQRトークンを取得
        resp = self.client.post("/api/v1/sessions", json={...}, headers=RECEPTION_HEADERS)
        self.qr_token = resp.json()["data"]["qr_token"]
        self.session_id = resp.json()["data"]["session_id"]

    @task(3)
    def view_session_info(self):
        with self.client.get(
            f"/api/v1/sessions/{self.qr_token}/info",
            catch_response=True
        ) as response:
            if response.elapsed.total_seconds() > 2.0:
                response.failure(f"レスポンス遅延: {response.elapsed.total_seconds()}s")
            elif response.status_code != 200:
                response.failure(f"ステータスエラー: {response.status_code}")

    @task(1)
    def submit_response(self):
        with self.client.post(
            f"/api/v1/sessions/{self.session_id}/responses",
            json=VALID_RESPONSE_PAYLOAD,
            catch_response=True
        ) as response:
            if response.elapsed.total_seconds() > 3.0:
                response.failure(f"送信遅延: {response.elapsed.total_seconds()}s")
```

**性能基準:**

| 指標 | 目標値 | 測定条件 |
|------|--------|---------|
| 問診フォーム表示 | P95 < 2秒 | 同時100ユーザー |
| 問診回答送信 | P95 < 3秒 | 同時100ユーザー |
| ダッシュボード表示 | P95 < 2秒 | 同時50ユーザー |
| PDF生成 | P95 < 10秒 | 同時10リクエスト |
| エラー率 | < 0.1% | 全リクエスト |

---

### TC-PERF-002: DB接続プールの枯渇テスト

| 優先度 | 中 | 種別 | 性能テスト |

```python
@task
def concurrent_db_stress_test(self):
    """100同時接続でDBコネクションプールが枯渇しないこと"""
    responses = []
    for _ in range(100):
        response = self.client.get(
            "/api/v1/dashboard/sessions",
            headers=DOCTOR_HEADERS,
            params={"date": "2026-03-28"}
        )
        responses.append(response.status_code)

    # 500エラーが0件であること（コネクション枯渇なし）
    assert all(s != 500 for s in responses)
```

---

## 15. アクセシビリティテスト (A11Y)

### TC-A11Y-001: 患者向け画面のaxe自動検査

| 優先度 | 高 | 種別 | アクセシビリティ (axe-playwright) |

```typescript
import AxeBuilder from "@axe-core/playwright";

test("患者問診フォームにWCAG 2.1 AA違反がないこと", async ({ page }) => {
  await page.goto(`http://localhost:3000/inquiry?token=${VALID_TOKEN}`);
  await page.getByRole("button", { name: "問診票を記入する" }).click();

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();

  // 違反0件
  expect(results.violations).toHaveLength(0);
});

test("医師用ダッシュボードにWCAG 2.1 AA違反がないこと", async ({ page }) => {
  await loginAs(page, "doctor@hospital.test");
  await page.goto("http://localhost:3000/dashboard");

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();

  expect(results.violations).toHaveLength(0);
});
```

---

### TC-A11Y-002: タッチターゲットサイズ

| 優先度 | 高 | 種別 | アクセシビリティ |

```typescript
test("患者向けボタンのタッチターゲットが44x44px以上である", async ({ page }) => {
  await page.goto(`http://localhost:3000/inquiry?token=${VALID_TOKEN}`);

  const submitButton = page.getByRole("button", { name: "問診票を記入する" });
  const boundingBox = await submitButton.boundingBox();

  expect(boundingBox?.width).toBeGreaterThanOrEqual(44);
  expect(boundingBox?.height).toBeGreaterThanOrEqual(44);
});
```

---

### TC-A11Y-003: フォーカス管理

| 優先度 | 高 | 種別 | アクセシビリティ |

```typescript
test("動的展開された追加質問にフォーカスが移る", async ({ page }) => {
  await page.goto(`http://localhost:3000/inquiry/form/department?session_id=${SESSION_ID}`);

  // 「はい」を選択
  await page.getByLabel("発熱: はい").check();

  // 展開されたフィールドにフォーカスが移っていること
  const focused = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  expect(focused).toBe("最高体温（℃）");
});
```

---

### TC-A11Y-004: エラーメッセージのスクリーンリーダー対応

| 優先度 | 高 | 種別 | アクセシビリティ |

```typescript
test("バリデーションエラーがrole=alertで通知される", async ({ page }) => {
  await page.goto(`http://localhost:3000/inquiry/form/common?session_id=${SESSION_ID}`);

  // 必須項目を空のまま「次へ」
  await page.getByRole("button", { name: "次へ" }).click();

  const alertElement = page.locator("[role='alert']");
  await expect(alertElement).toBeVisible();
  await expect(alertElement).toHaveText(/入力してください/);
});
```

---

## 16. 品質基準・合格条件

### 16.1 カバレッジ基準

| 対象 | 目標カバレッジ | 計測方法 |
|------|-------------|---------|
| バックエンド（全体） | **80%以上** | pytest-cov |
| バックエンド（認証・暗号化モジュール） | **95%以上** | pytest-cov |
| バックエンド（サービス層） | **90%以上** | pytest-cov |
| フロントエンド（コンポーネント） | **70%以上** | Vitest coverage |

### 16.2 テストケース合格基準

| フェーズ | 合格条件 |
|---------|---------|
| 開発中 | 実装済みAPIは関連テスト全て PASS |
| Phase 4 UAT前 | 全自動テスト PASS、カバレッジ基準達成 |
| 性能テスト | P95レスポンスタイム全指標達成・エラー率0.1%以下 |
| セキュリティ診断 | Critical / High 脆弱性 0件 |
| アクセシビリティ | axe-playwright による WCAG 2.1 AA 違反 0件 |
| リリース判定 | 上記全て達成 |

### 16.3 バグ優先度と対応期限

| 優先度 | 定義 | 対応期限 |
|--------|------|---------|
| P1（Critical） | データ漏洩・暗号化不備・認証突破 | 即日対応・リリースブロッカー |
| P2（High） | 主要機能の動作不良・セキュリティ脆弱性 | 翌営業日・UAT前に修正必須 |
| P3（Medium） | 非主要機能の不具合・UX問題 | 次スプリント内 |
| P4（Low） | 軽微なUI不具合・テキスト誤字 | バックログ管理 |

---

## 17. テスト実施計画

### 17.1 フェーズ別テスト実施

| フェーズ | 期間 | テスト内容 | 担当 |
|---------|------|-----------|------|
| Phase 1（基盤） | 1ヶ月目 | 認証API・暗号化単体テスト | 開発者 |
| Phase 2（コア） | 2ヶ月目 | 全APIテスト・コンポーネントテスト | 開発者 |
| Phase 3（連携） | 3ヶ月目 | AI・FHIR連携テスト・E2Eテスト | 開発者 |
| Phase 4（UAT） | 4ヶ月目 | ユーザー受け入れテスト・性能テスト・セキュリティ診断 | QA + 開発者 + 病院スタッフ |
| Phase 5（リリース前） | 5ヶ月目 | 回帰テスト・アクセシビリティ検査 | QA |

### 17.2 CI/CD自動テスト設定

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: inquiry_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5433:5432"]
      redis:
        image: redis:7
        ports: ["6380:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && pytest --cov=app --cov-fail-under=80 -v
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5433/inquiry_test
          REDIS_URL: redis://localhost:6380/1

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci && npm run test -- --coverage

  e2e-test:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up -d
      - run: cd frontend && npx playwright install --with-deps chromium
      - run: cd frontend && npx playwright test
```

### 17.3 テストケース集計

| カテゴリ | テストケース数 | 優先度H | 優先度M | 優先度L |
|---------|-------------|--------|--------|--------|
| AUTH | 9 | 7 | 2 | 0 |
| PAT | 10 | 8 | 2 | 0 |
| REC | 8 | 6 | 2 | 0 |
| DASH | 5 | 4 | 1 | 0 |
| ADM | 7 | 6 | 1 | 0 |
| SVC | 8 | 7 | 1 | 0 |
| SEC | 8 | 7 | 1 | 0 |
| FE | 5 | 4 | 1 | 0 |
| E2E | 3 | 3 | 0 | 0 |
| PERF | 2 | 1 | 1 | 0 |
| A11Y | 4 | 4 | 0 | 0 |
| **合計** | **69** | **57** | **12** | **0** |

---

*本テスト仕様書はCLAUDE.mdの開発規約（Red-Green-Refactor・実DB使用・モックDB禁止）に準拠して作成されています。テスト実装時は本書のアサーション例をそのまま使用するのではなく、実際の実装に合わせて調整してください。*
