# API仕様書
## デジタル問診システム (Medical Inquiry System)

| 項目 | 内容 |
|------|------|
| 文書バージョン | 1.0.0 |
| 作成日 | 2026-03-28 |
| APIバージョン | v1 |
| 仕様書形式 | OpenAPI 3.1（`docs/openapi.yaml` が機械可読版） |

---

## 目次

1. [概要](#1-概要)
2. [認証・認可](#2-認証認可)
3. [共通仕様](#3-共通仕様)
4. [エンドポイント一覧](#4-エンドポイント一覧)
5. [認証API](#5-認証api)
6. [患者向けAPI](#6-患者向けapi)
7. [受付スタッフAPI](#7-受付スタッフapi)
8. [医師用ダッシュボードAPI](#8-医師用ダッシュボードapi)
9. [管理者API - フォーム管理](#9-管理者api--フォーム管理)
10. [管理者API - スタッフ管理](#10-管理者api--スタッフ管理)
11. [管理者API - 監査・設定](#11-管理者api--監査設定)
12. [エラーコード一覧](#12-エラーコード一覧)

---

## 1. 概要

### 1.1 ベースURL

| 環境 | ベースURL |
|------|---------|
| 開発 | `http://localhost:8000/api/v1` |
| ステージング | `https://api-stg.inquiry.hospital.example.com/api/v1` |
| 本番 | `https://api.inquiry.hospital.example.com/api/v1` |

### 1.2 プロトコル・仕様

- プロトコル: **HTTPS**（本番・ステージング。開発はHTTP可）
- データ形式: **JSON**（`Content-Type: application/json`）
- 文字コード: **UTF-8**
- タイムゾーン: タイムスタンプはすべて **ISO 8601 (UTC)** で送受信（例: `2026-03-28T10:30:00Z`）
- APIバージョニング: URLパスにバージョンを含める（`/api/v1/...`）

### 1.3 APIカテゴリと利用者

| カテゴリ | パスプレフィックス | 主な利用者 |
|---------|-----------------|----------|
| 認証 | `/api/v1/auth` | スタッフ全員 |
| 患者向け | `/api/v1/sessions/{token}/info`, `/api/v1/departments/{code}/form`, `/api/v1/sessions/{id}/responses` | 患者（QRトークン認証） |
| 受付スタッフ | `/api/v1/sessions`, `/api/v1/sessions/{id}` | reception, admin |
| 医師用 | `/api/v1/dashboard`, `/api/v1/responses`, `/api/v1/patients` | doctor, admin |
| 管理者 | `/api/v1/admin` | admin |
| 共通マスタ | `/api/v1/departments` | スタッフ全員 |

---

## 2. 認証・認可

### 2.1 スタッフ認証（JWT Bearer）

スタッフ向けAPIはすべてJWT Bearer認証が必要。

```
Authorization: Bearer {access_token}
```

| トークン種別 | 有効期限 | 保存場所 |
|------------|---------|---------|
| アクセストークン | 15分 | メモリ（JavaScript変数） |
| リフレッシュトークン | 8時間 | HttpOnly Cookie（SameSite=Strict） |

**トークンリフレッシュフロー:**

```
クライアント                         APIサーバー
    │                                    │
    │── GET /api/v1/auth/refresh ──────→ │ ← Cookie の refresh_token を検証
    │                                    │
    │←── 200 { access_token: "..." } ── │ ← 新しいアクセストークンを返す
    │    （新しいリフレッシュトークンは  │   リフレッシュトークンはローテーション
    │     Set-Cookie で更新）            │
```

**アクセストークンペイロード（JWTクレーム）:**

```json
{
  "sub": "staff-user-uuid",
  "role": "doctor",
  "department_ids": ["uuid-naika", "uuid-geka"],
  "iat": 1743155400,
  "exp": 1743156300
}
```

### 2.2 患者向け認証（QRトークン）

患者向けAPIはBearerトークン不要。QRトークン（UUID v4）をURLまたはリクエストボディで渡す。

```
GET /api/v1/sessions/{qr_token}/info
```

QRトークンはRedisで管理し、有効期限・使用済みフラグをサーバー側で検証する。

### 2.3 ロールベースアクセス制御（RBAC）

| ロール | アクセス範囲 |
|--------|------------|
| `patient` | 患者向けAPI のみ（QRトークンで識別） |
| `reception` | 受付API + 共通マスタ |
| `nurse` | 問診状況一覧（読み取り）+ 共通マスタ |
| `doctor` | 医師用API + 受付の読み取り + 共通マスタ |
| `admin` | 全API |

ロール不足時は `403 Forbidden` を返す。

---

## 3. 共通仕様

### 3.1 レスポンスフォーマット

**成功時:**

```json
{
  "data": { /* リソースオブジェクト または 配列 */ },
  "meta": {
    "request_id": "req-550e8400-e29b-41d4",
    "timestamp": "2026-03-28T01:30:00Z"
  },
  "error": null
}
```

**一覧取得（ページネーションあり）:**

```json
{
  "data": [ /* 配列 */ ],
  "meta": {
    "request_id": "req-550e8400-e29b-41d4",
    "timestamp": "2026-03-28T01:30:00Z",
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 342,
      "total_pages": 18
    }
  },
  "error": null
}
```

**エラー時（RFC 7807 Problem Details 準拠）:**

```json
{
  "data": null,
  "meta": {
    "request_id": "req-550e8400-e29b-41d4",
    "timestamp": "2026-03-28T01:30:00Z"
  },
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力内容に誤りがあります",
    "details": [
      {
        "field": "email",
        "message": "メールアドレスの形式が正しくありません"
      }
    ]
  }
}
```

### 3.2 HTTPステータスコード

| コード | 意味 | 使用場面 |
|--------|------|---------|
| 200 | OK | GET・PATCH・PUT 成功 |
| 201 | Created | POST でリソース作成成功 |
| 204 | No Content | DELETE 成功 |
| 400 | Bad Request | バリデーションエラー・パラメータ不正 |
| 401 | Unauthorized | 未認証・トークン期限切れ |
| 403 | Forbidden | ロール権限不足 |
| 404 | Not Found | リソースが存在しない |
| 409 | Conflict | 一意制約違反・状態遷移不可 |
| 422 | Unprocessable Entity | 業務ロジックエラー |
| 429 | Too Many Requests | レート制限 |
| 500 | Internal Server Error | サーバー内部エラー |

### 3.3 共通クエリパラメータ（一覧API）

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `page` | integer | 1 | ページ番号（1始まり） |
| `per_page` | integer | 20 | 1ページあたり件数（最大100） |

### 3.4 リクエストID

全リクエストに `X-Request-ID` ヘッダーを付けることを推奨（未付与の場合はサーバーが採番）。ログ・監査との紐付けに使用する。

```
X-Request-ID: req-550e8400-e29b-41d4
```

### 3.5 レート制限

| エンドポイント群 | 上限 | 単位 |
|----------------|------|------|
| 患者向けAPI | 60 req | /分/IPアドレス |
| スタッフ認証API | 10 req | /分/IPアドレス |
| スタッフ向けAPI | 300 req | /分/ユーザー |
| 管理者API | 600 req | /分/ユーザー |
| PDF出力 | 30 req | /分/ユーザー |
| Claude API連携（内部） | 60 req | /分 |

超過時は `429 Too Many Requests` + `Retry-After` ヘッダーを返す。

---

## 4. エンドポイント一覧

| # | メソッド | パス | 概要 | ロール |
|---|---------|------|------|--------|
| **認証** |
| 1 | POST | `/auth/login` | スタッフログイン | — |
| 2 | POST | `/auth/logout` | ログアウト | 全スタッフ |
| 3 | POST | `/auth/refresh` | トークンリフレッシュ | 全スタッフ |
| 4 | POST | `/auth/reset-password/request` | PW リセット申請 | — |
| 5 | POST | `/auth/reset-password/confirm` | PW リセット確定 | — |
| **患者向け** |
| 6 | GET | `/sessions/{token}/info` | QRトークン検証・セッション情報 | patient |
| 7 | GET | `/departments/{code}/form` | 診療科フォーム定義取得 | patient |
| 8 | POST | `/sessions/{session_id}/responses` | 問診回答送信 | patient |
| **受付スタッフ** |
| 9 | POST | `/sessions` | QRコード発行 | reception, admin |
| 10 | GET | `/sessions` | 問診セッション一覧 | reception, nurse, admin |
| 11 | PATCH | `/sessions/{id}` | セッションステータス更新 | reception, admin |
| 12 | POST | `/sessions/{id}/reissue-qr` | QRコード再発行 | reception, admin |
| 13 | GET | `/sessions/{id}/qr.png` | QRコード画像取得 | reception, admin |
| **医師用** |
| 14 | GET | `/dashboard/sessions` | 患者一覧（本日） | doctor, admin |
| 15 | GET | `/dashboard/sessions/{session_id}` | 患者詳細・問診回答 | doctor, admin |
| 16 | GET | `/responses/{id}/pdf` | PDF出力 | doctor, admin |
| 17 | GET | `/patients/{patient_id}/sessions` | 過去問診履歴 | doctor, admin |
| **共通マスタ** |
| 18 | GET | `/departments` | 診療科一覧 | 全スタッフ |
| **管理者 - フォーム** |
| 19 | GET | `/admin/forms` | フォーム一覧 | admin |
| 20 | POST | `/admin/forms` | フォーム新規作成 | admin |
| 21 | GET | `/admin/forms/{id}` | フォーム詳細取得 | admin |
| 22 | PUT | `/admin/forms/{id}` | フォーム更新 | admin |
| 23 | POST | `/admin/forms/{id}/publish` | フォーム公開 | admin |
| 24 | POST | `/admin/forms/{id}/duplicate` | フォーム複製 | admin |
| **管理者 - スタッフ** |
| 25 | GET | `/admin/staff` | スタッフ一覧 | admin |
| 26 | POST | `/admin/staff` | スタッフ作成 | admin |
| 27 | GET | `/admin/staff/{id}` | スタッフ詳細 | admin |
| 28 | PUT | `/admin/staff/{id}` | スタッフ更新 | admin |
| 29 | PATCH | `/admin/staff/{id}/status` | 有効/無効切替 | admin |
| **管理者 - 監査・設定** |
| 30 | GET | `/admin/audit-logs` | 監査ログ一覧 | admin |
| 31 | GET | `/admin/audit-logs/export` | 監査ログCSVエクスポート | admin |
| 32 | GET | `/admin/settings` | システム設定取得 | admin |
| 33 | PUT | `/admin/settings` | システム設定更新 | admin |

---

## 5. 認証API

### `POST /auth/login`

スタッフのログイン認証。成功時はアクセストークンを返し、リフレッシュトークンをHttpOnly Cookieにセットする。

**認証:** 不要

**リクエスト:**

```json
{
  "email": "yamada@hospital.example.com",
  "password": "P@ssw0rd!"
}
```

**レスポンス `200 OK`:**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "yamada@hospital.example.com",
      "full_name": "山田 太郎",
      "role": "doctor",
      "department_ids": ["uuid-naika"]
    }
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

**Set-Cookie レスポンスヘッダー:**

```
Set-Cookie: refresh_token={token}; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=28800
```

**エラーケース:**

| 条件 | ステータス | error.code |
|------|----------|-----------|
| メール・パスワード不一致 | 401 | `INVALID_CREDENTIALS` |
| アカウントロック中 | 403 | `ACCOUNT_LOCKED` |
| アカウント無効 | 403 | `ACCOUNT_DISABLED` |

---

### `POST /auth/logout`

アクセストークンを無効化し、リフレッシュトークンCookieを削除する。

**認証:** Bearer

**リクエスト:** なし

**レスポンス `200 OK`:**

```json
{
  "data": { "message": "ログアウトしました" },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `POST /auth/refresh`

リフレッシュトークン（Cookie）を使ってアクセストークンを再発行する。トークンローテーションにより毎回新しいリフレッシュトークンを発行。

**認証:** Cookie（`refresh_token`）

**リクエスト:** なし

**レスポンス `200 OK`:**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 900
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

**エラーケース:**

| 条件 | ステータス | error.code |
|------|----------|-----------|
| Cookieなし / 無効 | 401 | `INVALID_REFRESH_TOKEN` |
| 有効期限切れ | 401 | `REFRESH_TOKEN_EXPIRED` |
| 失効済み（再利用攻撃） | 401 | `REFRESH_TOKEN_REVOKED` |

---

### `POST /auth/reset-password/request`

パスワードリセット用メールを送信する。メールアドレスが存在しない場合も200を返す（ユーザー存在確認の防止）。

**認証:** 不要

**リクエスト:**

```json
{
  "email": "yamada@hospital.example.com"
}
```

**レスポンス `200 OK`:**

```json
{
  "data": { "message": "メールを送信しました（登録済みの場合）" },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `POST /auth/reset-password/confirm`

メールのリセットトークンを使ってパスワードを変更する。

**認証:** 不要（リセットトークンで識別）

**リクエスト:**

```json
{
  "reset_token": "base64encodedtoken...",
  "new_password": "NewP@ssw0rd!",
  "new_password_confirm": "NewP@ssw0rd!"
}
```

**バリデーション:**

| 項目 | ルール |
|------|--------|
| reset_token | 必須・有効期限30分以内 |
| new_password | 必須・8文字以上・大文字小文字数字記号を各1文字以上含む |
| new_password_confirm | new_password と一致 |

**レスポンス `200 OK`:**

```json
{
  "data": { "message": "パスワードを変更しました" },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

## 6. 患者向けAPI

> **注意:** 患者向けAPIはJWT認証不要。QRトークン（UUID v4）をパスまたはボディで渡す。

### `GET /sessions/{token}/info`

QRコードのトークンを検証し、問診開始に必要な情報を返す。

**認証:** QRトークン（パスパラメータ）

**パスパラメータ:**

| 名前 | 型 | 説明 |
|------|-----|------|
| `token` | string (UUID v4) | QRコードに埋め込まれたトークン |

**レスポンス `200 OK`:**

```json
{
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "patient_name": "田中 花子",
    "department_name": "内科",
    "department_code": "naika",
    "appointment_at": "2026-03-28T01:30:00Z",
    "doctor_name": "山田 太郎",
    "form_definition_id": "uuid-form-v3",
    "qr_expires_at": "2026-03-28T15:00:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

**エラーケース:**

| 条件 | ステータス | error.code |
|------|----------|-----------|
| 存在しないトークン | 404 | `INVALID_TOKEN` |
| 有効期限切れ | 422 | `TOKEN_EXPIRED` |
| 使用済み | 422 | `ALREADY_COMPLETED` |
| キャンセル済み | 422 | `SESSION_CANCELLED` |

---

### `GET /departments/{code}/form`

患者の問診フォームに使用するフォーム定義を取得する。現在公開中のバージョンを返す。

**認証:** QRトークン（クエリパラメータ `session_id` で間接的に検証）

**パスパラメータ:**

| 名前 | 型 | 説明 |
|------|-----|------|
| `code` | string | 診療科コード（例: `naika`, `geka`） |

**クエリパラメータ:**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `session_id` | string (UUID) | ○ | セッションIDでアクセス権を確認 |

**レスポンス `200 OK`:**

```json
{
  "data": {
    "form_definition_id": "uuid-form",
    "department_code": "naika",
    "department_name": "内科",
    "version": 3,
    "schema": {
      "title": "内科問診票 v3",
      "sections": [
        {
          "id": "common_basic",
          "title": "基本情報",
          "questions": [
            {
              "id": "q_chief_complaint",
              "type": "textarea",
              "label": "今日の受診理由を教えてください",
              "required": true,
              "validation": { "max_length": 500 },
              "placeholder": "例: 3日前から発熱と咳が続いています"
            },
            {
              "id": "q_onset",
              "type": "radio",
              "label": "症状はいつ頃から始まりましたか？",
              "required": true,
              "options": [
                { "value": "today", "label": "今日" },
                { "value": "few_days", "label": "数日前" },
                { "value": "week_plus", "label": "1週間以上前" },
                { "value": "month_plus", "label": "1ヶ月以上前" }
              ]
            }
          ]
        },
        {
          "id": "dept_specific",
          "title": "内科専用の質問",
          "questions": [
            {
              "id": "q_fever",
              "type": "radio",
              "label": "発熱はありますか？",
              "required": true,
              "options": [
                { "value": "yes", "label": "はい" },
                { "value": "no", "label": "いいえ" }
              ],
              "branches": [
                {
                  "condition": { "operator": "eq", "value": "yes" },
                  "show_question_ids": ["q_max_temp", "q_antipyretic"]
                }
              ]
            },
            {
              "id": "q_max_temp",
              "type": "number",
              "label": "最高体温（℃）",
              "required": true,
              "visible_by_default": false,
              "validation": { "min": 35.0, "max": 42.0 }
            }
          ]
        }
      ]
    }
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `POST /sessions/{session_id}/responses`

患者の問診回答を送信する。受信後、非同期でAI分析とFHIR同期を開始する。

**認証:** セッションID（パスパラメータ）+ Redisでのセッション状態確認

**パスパラメータ:**

| 名前 | 型 | 説明 |
|------|-----|------|
| `session_id` | string (UUID) | セッションID |

**リクエスト:**

```json
{
  "form_definition_id": "uuid-form-v3",
  "common_answers": {
    "q_chief_complaint": "3日前から発熱と咳が続いています",
    "q_onset": "few_days",
    "q_severity": 6,
    "q_past_illness": ["hypertension"],
    "q_past_illness_other": "",
    "q_surgery_history": false,
    "q_drug_allergy": true,
    "q_drug_allergy_detail": "ペニシリン系（アナフィラキシー歴あり）",
    "q_food_allergy": false,
    "q_current_medication": true,
    "q_medication_detail": "ワーファリン 2mg/日",
    "q_supplement": false,
    "q_smoking": "never",
    "q_alcohol": "occasional",
    "q_exercise": "few_times_week",
    "q_insurance_type": "shakai_hoken",
    "q_consent_privacy": true,
    "q_consent_ai": true
  },
  "department_answers": {
    "q_fever": "yes",
    "q_max_temp": 38.5,
    "q_antipyretic": "no",
    "q_cough": "yes",
    "q_cough_type": "wet",
    "q_bloody_sputum": "no",
    "q_chest_pain": "no",
    "q_nausea": "no",
    "q_diarrhea": "no"
  }
}
```

**バリデーション:**

| 項目 | ルール |
|------|--------|
| form_definition_id | セッションのform_definition_idと一致すること |
| q_consent_privacy | `true` 必須 |
| q_consent_ai | `true` 必須 |
| フォームスキーマの required 項目 | 全て必須 |
| 数値項目 | スキーマの min/max 範囲内 |

**レスポンス `201 Created`:**

```json
{
  "data": {
    "response_id": "uuid-response",
    "session_id": "uuid-session",
    "ai_status": "pending",
    "fhir_sync_status": "pending",
    "created_at": "2026-03-28T01:35:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

**エラーケース:**

| 条件 | ステータス | error.code |
|------|----------|-----------|
| セッション未開始 / キャンセル済み | 422 | `SESSION_NOT_IN_PROGRESS` |
| 回答済み | 409 | `RESPONSE_ALREADY_EXISTS` |
| バリデーション失敗 | 400 | `VALIDATION_ERROR` |
| 同意未チェック | 400 | `CONSENT_REQUIRED` |

---

## 7. 受付スタッフAPI

### `POST /sessions`

患者のQRコード付き問診セッションを新規発行する。

**認証:** Bearer（reception / admin）

**リクエスト:**

```json
{
  "external_patient_id": "000123",
  "department_id": "uuid-naika",
  "appointment_at": "2026-03-28T01:30:00Z"
}
```

**バリデーション:**

| 項目 | ルール |
|------|--------|
| external_patient_id | 必須・1〜50文字 |
| department_id | 必須・存在する診療科 |
| appointment_at | 必須・過去日時不可 |

**レスポンス `201 Created`:**

```json
{
  "data": {
    "session_id": "uuid-session",
    "external_patient_id": "000123",
    "department_id": "uuid-naika",
    "department_name": "内科",
    "appointment_at": "2026-03-28T01:30:00Z",
    "qr_token": "550e8400-e29b-41d4-a716-446655440000",
    "qr_image_url": "/api/v1/sessions/uuid-session/qr.png",
    "qr_url": "https://inquiry.hospital.example.com/inquiry?token=550e8400...",
    "qr_expires_at": "2026-03-28T15:00:00Z",
    "status": "pending"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

**エラーケース:**

| 条件 | ステータス | error.code |
|------|----------|-----------|
| 同一患者・科・日時のセッション重複 | 409 | `SESSION_ALREADY_EXISTS` |
| 診療科が無効 | 422 | `DEPARTMENT_INACTIVE` |
| 公開中フォームなし | 422 | `NO_PUBLISHED_FORM` |

---

### `GET /sessions`

本日の問診セッション一覧を取得する。

**認証:** Bearer（reception / nurse / admin）

**クエリパラメータ:**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `date` | string (YYYY-MM-DD) | — | 対象日（デフォルト: 本日） |
| `department_id` | string (UUID) | — | 診療科でフィルタ |
| `status` | string | — | `pending`, `in_progress`, `completed`, `cancelled`, `expired` |
| `search` | string | — | 患者IDで部分検索 |
| `page` | integer | — | ページ番号 |
| `per_page` | integer | — | 1ページ件数（max 100） |

**レスポンス `200 OK`:**

```json
{
  "data": [
    {
      "session_id": "uuid-session-1",
      "external_patient_id": "000456",
      "department_name": "内科",
      "appointment_at": "2026-03-28T01:00:00Z",
      "status": "in_progress",
      "started_at": "2026-03-28T01:12:00Z",
      "completed_at": null,
      "minutes_elapsed": 23,
      "is_overdue": false
    },
    {
      "session_id": "uuid-session-2",
      "external_patient_id": "000789",
      "department_name": "内科",
      "appointment_at": "2026-03-28T01:45:00Z",
      "status": "completed",
      "started_at": "2026-03-28T01:40:00Z",
      "completed_at": "2026-03-28T01:52:00Z",
      "minutes_elapsed": null,
      "is_overdue": false
    }
  ],
  "meta": {
    "request_id": "...",
    "timestamp": "...",
    "pagination": { "page": 1, "per_page": 20, "total": 42, "total_pages": 3 },
    "summary": {
      "total": 42,
      "by_status": {
        "pending": 15,
        "in_progress": 5,
        "completed": 20,
        "cancelled": 2,
        "expired": 0
      }
    }
  },
  "error": null
}
```

---

### `PATCH /sessions/{id}`

セッションのステータスを更新する（キャンセル等）。

**認証:** Bearer（reception / admin）

**パスパラメータ:** `id` = セッションID（UUID）

**リクエスト:**

```json
{
  "status": "cancelled"
}
```

**バリデーション:**

| 更新可能なステータス | 条件 |
|--------------------|------|
| `cancelled` | `pending` または `in_progress` のみ |

**レスポンス `200 OK`:**

```json
{
  "data": {
    "session_id": "uuid-session",
    "status": "cancelled",
    "updated_at": "2026-03-28T01:30:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `POST /sessions/{id}/reissue-qr`

期限切れまたはキャンセルされたセッションにQRコードを再発行する。旧セッションはexpiredに更新し、新セッションを作成する。

**認証:** Bearer（reception / admin）

**パスパラメータ:** `id` = 元のセッションID

**リクエスト:** なし

**レスポンス `201 Created`:**

```json
{
  "data": {
    "new_session_id": "uuid-new-session",
    "qr_token": "new-uuid-token",
    "qr_image_url": "/api/v1/sessions/uuid-new-session/qr.png",
    "qr_expires_at": "2026-03-28T15:00:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `GET /sessions/{id}/qr.png`

QRコードをPNG画像として取得する（印刷用）。

**認証:** Bearer（reception / admin）

**パスパラメータ:** `id` = セッションID

**クエリパラメータ:**

| 名前 | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `size` | integer | 300 | 画像サイズ（px）。最大1000 |

**レスポンス `200 OK`:**

```
Content-Type: image/png
Body: [PNG バイナリ]
```

---

## 8. 医師用ダッシュボードAPI

### `GET /dashboard/sessions`

本日の担当診療科の患者一覧を取得する。要注意フラグ付き患者を上位に表示。

**認証:** Bearer（doctor / admin）

**クエリパラメータ:**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `date` | string (YYYY-MM-DD) | — | 対象日（デフォルト: 本日） |
| `department_id` | string (UUID) | — | 診療科（doctor は担当科のみ） |
| `status` | string | — | セッションステータス |
| `ai_status` | string | — | `pending`, `processing`, `completed`, `failed` |
| `has_risk_flags` | boolean | — | `true` で要注意患者のみ |

**レスポンス `200 OK`:**

```json
{
  "data": [
    {
      "session_id": "uuid-session-1",
      "external_patient_id": "000456",
      "patient_name": "田中 花子",
      "department_name": "内科",
      "appointment_at": "2026-03-28T01:00:00Z",
      "session_status": "completed",
      "ai_status": "completed",
      "risk_flags": [
        { "type": "drug_allergy", "label": "薬剤アレルギー", "severity": "high" },
        { "type": "medication_risk", "label": "服薬リスク", "severity": "medium" }
      ],
      "has_risk_flags": true
    },
    {
      "session_id": "uuid-session-2",
      "external_patient_id": "001234",
      "patient_name": "佐藤 美咲",
      "department_name": "内科",
      "appointment_at": "2026-03-28T01:30:00Z",
      "session_status": "completed",
      "ai_status": "processing",
      "risk_flags": [],
      "has_risk_flags": false
    }
  ],
  "meta": {
    "request_id": "...",
    "timestamp": "...",
    "pagination": { "page": 1, "per_page": 20, "total": 18, "total_pages": 1 },
    "summary": {
      "total_with_risk_flags": 3,
      "ai_completed": 8,
      "ai_processing": 2
    }
  },
  "error": null
}
```

---

### `GET /dashboard/sessions/{session_id}`

患者の問診回答詳細とAIサマリーを取得する（医師用詳細画面）。

**認証:** Bearer（doctor / admin）

**パスパラメータ:** `session_id` = セッションID（UUID）

**レスポンス `200 OK`:**

```json
{
  "data": {
    "session": {
      "session_id": "uuid-session",
      "appointment_at": "2026-03-28T01:00:00Z",
      "department_name": "内科",
      "session_status": "completed",
      "completed_at": "2026-03-28T01:15:00Z"
    },
    "patient": {
      "patient_id": "uuid-patient",
      "external_patient_id": "000456",
      "name": "田中 花子",
      "gender": "female",
      "date_of_birth": "1975-08-15",
      "phone": "090-XXXX-XXXX"
    },
    "response": {
      "response_id": "uuid-response",
      "common_answers": {
        "q_chief_complaint": "3日前から発熱と咳が続いています",
        "q_onset": "few_days",
        "q_severity": 6,
        "q_past_illness": ["hypertension"],
        "q_drug_allergy": true,
        "q_drug_allergy_detail": "ペニシリン系（アナフィラキシー歴あり）",
        "q_current_medication": true,
        "q_medication_detail": "ワーファリン 2mg/日"
      },
      "department_answers": {
        "q_fever": "yes",
        "q_max_temp": 38.5,
        "q_cough": "yes",
        "q_cough_type": "wet"
      },
      "submitted_at": "2026-03-28T01:15:00Z"
    },
    "ai_summary": {
      "status": "completed",
      "symptom_summary": "患者は3日前から発熱（38.5℃）と湿性の咳を訴えている。症状の程度は10段階中6。",
      "risk_flags": [
        {
          "type": "drug_allergy",
          "severity": "high",
          "label": "薬剤アレルギー",
          "detail": "ペニシリン系（アナフィラキシー歴あり）"
        },
        {
          "type": "medication_risk",
          "severity": "medium",
          "label": "服薬リスク",
          "detail": "ワーファリン服用中（出血リスク）"
        }
      ],
      "recommendations": [
        "抗生剤選択時のアレルギー歴確認",
        "ワーファリン用量・PT-INR値の確認",
        "喀痰培養検査の検討"
      ],
      "diff_from_previous": {
        "previous_session_id": "uuid-prev-session",
        "previous_date": "2025-12-15",
        "new_symptoms": ["発熱", "咳"],
        "resolved_symptoms": [],
        "summary": "前回（2025-12-15）と比較して、発熱・咳が新規症状として確認された。"
      },
      "model": "claude-sonnet-4-6",
      "input_tokens": 1245,
      "output_tokens": 387,
      "processed_at": "2026-03-28T01:16:30Z"
    },
    "fhir_resource_id": "QuestionnaireResponse/megaoak-12345",
    "fhir_sync_status": "synced"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

**AIサマリーが未完了の場合（ポーリング用）:**

```json
{
  "data": {
    "...（上記と同じ構造）...",
    "ai_summary": {
      "status": "processing",
      "symptom_summary": null,
      "risk_flags": [],
      "recommendations": [],
      "diff_from_previous": null,
      "processed_at": null
    }
  }
}
```

---

### `GET /responses/{id}/pdf`

問診回答票をPDFファイルとして返す（サーバーサイド生成）。

**認証:** Bearer（doctor / admin）

**パスパラメータ:** `id` = response_id（UUID）

**クエリパラメータ:**

| 名前 | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `include_ai_summary` | boolean | true | PDFにAIサマリーを含めるか |

**レスポンス `200 OK`:**

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="inquiry-000456-20260328.pdf"
Body: [PDF バイナリ]
```

---

### `GET /patients/{patient_id}/sessions`

患者の過去の問診セッション履歴を時系列（降順）で取得する。

**認証:** Bearer（doctor / admin）

**パスパラメータ:** `patient_id` = UUID

**クエリパラメータ:** `page`, `per_page`

**レスポンス `200 OK`:**

```json
{
  "data": [
    {
      "session_id": "uuid-session-latest",
      "department_name": "内科",
      "appointment_at": "2026-03-28T01:00:00Z",
      "session_status": "completed",
      "chief_complaint": "3日前から発熱と咳が続いています",
      "risk_flags": [
        { "type": "drug_allergy", "label": "薬剤アレルギー" }
      ],
      "ai_summary_excerpt": "発熱（38.5℃）と湿性の咳。ペニシリンアレルギー注意。"
    },
    {
      "session_id": "uuid-session-prev",
      "department_name": "内科",
      "appointment_at": "2025-12-15T02:00:00Z",
      "session_status": "completed",
      "chief_complaint": "頭痛と倦怠感",
      "risk_flags": [],
      "ai_summary_excerpt": "緊急フラグなし。頭痛・倦怠感を訴えている。"
    }
  ],
  "meta": {
    "request_id": "...",
    "timestamp": "...",
    "pagination": { "page": 1, "per_page": 20, "total": 5, "total_pages": 1 }
  },
  "error": null
}
```

---

## 9. 管理者API — フォーム管理

### `GET /admin/forms`

診療科ごとのフォーム定義一覧（全バージョン）を取得する。

**認証:** Bearer（admin）

**クエリパラメータ:**

| 名前 | 型 | 説明 |
|------|-----|------|
| `department_id` | string (UUID) | 診療科でフィルタ |
| `status` | string | `draft`, `published`, `archived` |

**レスポンス `200 OK`:**

```json
{
  "data": [
    {
      "form_definition_id": "uuid-form-v3",
      "department_id": "uuid-naika",
      "department_name": "内科",
      "version": 3,
      "status": "published",
      "published_at": "2026-02-10T00:00:00Z",
      "created_by_name": "管理者 田中",
      "created_at": "2026-02-08T10:00:00Z",
      "updated_at": "2026-02-09T15:00:00Z"
    }
  ],
  "meta": { "request_id": "...", "timestamp": "...", "pagination": { ... } },
  "error": null
}
```

---

### `POST /admin/forms`

新規フォーム定義を作成する（ドラフト状態で作成）。

**認証:** Bearer（admin）

**リクエスト:**

```json
{
  "department_id": "uuid-naika",
  "schema": { /* フォーム定義JSON（docs/form-schema.md参照）*/ }
}
```

**レスポンス `201 Created`:**

```json
{
  "data": {
    "form_definition_id": "uuid-form-new",
    "department_id": "uuid-naika",
    "version": 4,
    "status": "draft",
    "created_at": "2026-03-28T01:00:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `GET /admin/forms/{id}`

フォーム定義の詳細（スキーマ含む）を取得する。

**認証:** Bearer（admin）

**レスポンス `200 OK`:**

```json
{
  "data": {
    "form_definition_id": "uuid-form-v3",
    "department_id": "uuid-naika",
    "department_name": "内科",
    "version": 3,
    "status": "published",
    "schema": { /* 完全なフォーム定義JSON */ },
    "published_at": "2026-02-10T00:00:00Z",
    "created_by_name": "管理者 田中",
    "created_at": "2026-02-08T10:00:00Z",
    "updated_at": "2026-02-09T15:00:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `PUT /admin/forms/{id}`

フォーム定義を更新する（ドラフトのみ更新可能）。

**認証:** Bearer（admin）

**リクエスト:**

```json
{
  "schema": { /* 更新後のフォーム定義JSON */ }
}
```

**エラーケース:**

| 条件 | ステータス | error.code |
|------|----------|-----------|
| 公開・アーカイブ済みの更新 | 409 | `FORM_NOT_DRAFT` |

---

### `POST /admin/forms/{id}/publish`

ドラフトのフォームを公開する。同一診療科の現在公開中フォームはアーカイブに移行する。

**認証:** Bearer（admin）

**リクエスト:** なし

**レスポンス `200 OK`:**

```json
{
  "data": {
    "form_definition_id": "uuid-form-v4",
    "status": "published",
    "published_at": "2026-03-28T01:00:00Z",
    "archived_form_id": "uuid-form-v3"
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `POST /admin/forms/{id}/duplicate`

公開済みフォームをドラフトとして複製する（次バージョン編集の起点）。

**認証:** Bearer（admin）

**レスポンス `201 Created`:**

```json
{
  "data": {
    "new_form_definition_id": "uuid-form-v4",
    "department_id": "uuid-naika",
    "version": 4,
    "status": "draft",
    "copied_from_version": 3
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `GET /departments`

有効な診療科一覧を取得する。

**認証:** Bearer（全スタッフ）

**レスポンス `200 OK`:**

```json
{
  "data": [
    { "department_id": "uuid-naika", "name": "内科", "code": "naika", "display_order": 1 },
    { "department_id": "uuid-geka", "name": "外科・整形外科", "code": "geka", "display_order": 2 },
    { "department_id": "uuid-sanka", "name": "産婦人科", "code": "sanka_fujinka", "display_order": 3 },
    { "department_id": "uuid-shoni", "name": "小児科", "code": "shonika", "display_order": 4 }
  ],
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

## 10. 管理者API — スタッフ管理

### `GET /admin/staff`

スタッフアカウント一覧を取得する。

**認証:** Bearer（admin）

**クエリパラメータ:**

| 名前 | 型 | 説明 |
|------|-----|------|
| `role` | string | `admin`, `doctor`, `nurse`, `reception` |
| `is_active` | boolean | `true` / `false` |
| `search` | string | 氏名・メールで部分検索 |

**レスポンス `200 OK`:**

```json
{
  "data": [
    {
      "staff_id": "uuid-staff",
      "email": "yamada@hospital.example.com",
      "full_name": "山田 太郎",
      "role": "doctor",
      "department_names": ["内科"],
      "is_active": true,
      "last_login_at": "2026-03-28T00:30:00Z",
      "created_at": "2025-04-01T00:00:00Z"
    }
  ],
  "meta": { "request_id": "...", "timestamp": "...", "pagination": { ... } },
  "error": null
}
```

---

### `POST /admin/staff`

スタッフアカウントを新規作成する。初期パスワードはシステム生成してメール送信。

**認証:** Bearer（admin）

**リクエスト:**

```json
{
  "email": "sato@hospital.example.com",
  "full_name": "佐藤 次郎",
  "role": "doctor",
  "department_ids": ["uuid-naika", "uuid-geka"]
}
```

**バリデーション:**

| 項目 | ルール |
|------|--------|
| email | 必須・メール形式・重複不可 |
| full_name | 必須・1〜100文字 |
| role | 必須・有効値のみ |
| department_ids | roleが `reception` / `nurse` / `doctor` の場合は1件以上必須 |

**レスポンス `201 Created`:**

```json
{
  "data": {
    "staff_id": "uuid-new-staff",
    "email": "sato@hospital.example.com",
    "full_name": "佐藤 次郎",
    "role": "doctor",
    "is_active": true,
    "initial_password_sent": true
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `PUT /admin/staff/{id}`

スタッフ情報を更新する。パスワード変更はリセットフローで行う。

**認証:** Bearer（admin）

**リクエスト:**

```json
{
  "full_name": "佐藤 次郎",
  "role": "nurse",
  "department_ids": ["uuid-naika"]
}
```

---

### `PATCH /admin/staff/{id}/status`

スタッフの有効/無効を切り替える。

**認証:** Bearer（admin）

**リクエスト:**

```json
{
  "is_active": false
}
```

**バリデーション:**

- 自分自身を無効化することはできない（`403 Forbidden`）
- 最後のadminを無効化することはできない（`422 Unprocessable Entity`）

---

## 11. 管理者API — 監査・設定

### `GET /admin/audit-logs`

監査ログを検索・取得する。

**認証:** Bearer（admin）

**クエリパラメータ:**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `from` | string (YYYY-MM-DD) | ○ | 開始日 |
| `to` | string (YYYY-MM-DD) | ○ | 終了日（最大90日範囲） |
| `staff_user_id` | string (UUID) | — | 操作者でフィルタ |
| `action` | string | — | 操作種別でフィルタ |
| `resource_type` | string | — | リソース種別でフィルタ |
| `page` | integer | — | ページ番号 |
| `per_page` | integer | — | 1ページ件数（max 100） |

**レスポンス `200 OK`:**

```json
{
  "data": [
    {
      "log_id": "uuid-log",
      "staff_name": "山田 太郎",
      "staff_role": "doctor",
      "action": "read",
      "resource_type": "inquiry_response",
      "resource_id": "uuid-response",
      "details": null,
      "ip_address": "192.168.1.100",
      "created_at": "2026-03-28T00:42:31Z"
    }
  ],
  "meta": { "request_id": "...", "timestamp": "...", "pagination": { ... } },
  "error": null
}
```

---

### `GET /admin/audit-logs/export`

監査ログをCSVファイルとしてダウンロードする。

**認証:** Bearer（admin）

**クエリパラメータ:** `from`, `to`（必須、最大90日）, `staff_user_id`, `action`, `resource_type`

**レスポンス `200 OK`:**

```
Content-Type: text/csv; charset=UTF-8
Content-Disposition: attachment; filename="audit-logs-20260328.csv"
Body: [CSV テキスト]
```

**CSVヘッダー:**

```csv
ログID,日時,操作者,ロール,操作種別,リソース種別,リソースID,IPアドレス
```

---

### `GET /admin/settings`

システム設定を取得する。

**認証:** Bearer（admin）

**レスポンス `200 OK`:**

```json
{
  "data": {
    "hospital_name": "○○総合病院",
    "reception_phone": "03-XXXX-XXXX",
    "inquiry_overdue_minutes": 30,
    "ai_summary_enabled": true,
    "ai_disclaimer_text": "※ このサマリーはAIが生成した参考情報です。医師の診断・治療の指針を代替するものではありません。",
    "qr_validity_hours": 36
  },
  "meta": { "request_id": "...", "timestamp": "..." },
  "error": null
}
```

---

### `PUT /admin/settings`

システム設定を更新する。

**認証:** Bearer（admin）

**リクエスト:**

```json
{
  "hospital_name": "○○総合病院",
  "reception_phone": "03-XXXX-XXXX",
  "inquiry_overdue_minutes": 30,
  "ai_summary_enabled": true,
  "ai_disclaimer_text": "※ このサマリーはAIが生成した参考情報です。",
  "qr_validity_hours": 36
}
```

---

## 12. エラーコード一覧

| error.code | HTTPステータス | 説明 |
|-----------|--------------|------|
| `VALIDATION_ERROR` | 400 | リクエストのバリデーション失敗 |
| `CONSENT_REQUIRED` | 400 | 同意チェックが必要 |
| `INVALID_CREDENTIALS` | 401 | メール・パスワード不一致 |
| `TOKEN_EXPIRED` | 401 | アクセストークン期限切れ |
| `INVALID_REFRESH_TOKEN` | 401 | リフレッシュトークン無効 |
| `REFRESH_TOKEN_EXPIRED` | 401 | リフレッシュトークン期限切れ |
| `REFRESH_TOKEN_REVOKED` | 401 | リフレッシュトークン失効（再利用攻撃） |
| `INVALID_TOKEN` | 404 | QRトークン存在しない |
| `ACCOUNT_LOCKED` | 403 | アカウントロック中（5回失敗） |
| `ACCOUNT_DISABLED` | 403 | アカウント無効 |
| `PERMISSION_DENIED` | 403 | ロール権限不足 |
| `NOT_FOUND` | 404 | リソースが存在しない |
| `TOKEN_EXPIRED` | 422 | QRトークン有効期限切れ |
| `ALREADY_COMPLETED` | 422 | 問診完了済み |
| `SESSION_CANCELLED` | 422 | セッションキャンセル済み |
| `SESSION_NOT_IN_PROGRESS` | 422 | セッション未開始・完了・キャンセル済み |
| `DEPARTMENT_INACTIVE` | 422 | 診療科が無効 |
| `NO_PUBLISHED_FORM` | 422 | 公開中フォームなし |
| `SELF_DEACTIVATION` | 422 | 自分自身を無効化不可 |
| `LAST_ADMIN_DEACTIVATION` | 422 | 最後のadminを無効化不可 |
| `SESSION_ALREADY_EXISTS` | 409 | 同一患者・科・日時セッション重複 |
| `RESPONSE_ALREADY_EXISTS` | 409 | 回答送信済み |
| `FORM_NOT_DRAFT` | 409 | ドラフト以外のフォームは更新不可 |
| `RATE_LIMIT_EXCEEDED` | 429 | レート制限超過 |
| `INTERNAL_SERVER_ERROR` | 500 | サーバー内部エラー |
| `AI_ANALYSIS_FAILED` | 500 | Claude API呼び出し失敗 |
| `FHIR_SYNC_FAILED` | 500 | NEC MegaOakHR連携失敗 |

---

*本API仕様書はOpenAPI 3.1機械可読版 (`docs/openapi.yaml`) と合わせて参照してください。実装時はOpenAPI仕様書を正とし、差異がある場合はOpenAPI仕様書を優先してください。*
