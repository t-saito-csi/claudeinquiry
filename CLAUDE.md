# 問診システム (Medical Inquiry System) — CLAUDE.md

## プロジェクト概要

大規模病院向けのデジタル問診システム。患者が来院前（スマートフォン/PC）または来院時（受付端末）に問診票を記入し、医師が診察前に患者情報を把握できる仕組みを提供する。

### ターゲット
- **利用施設**: 大規模病院（複数診療科）
- **問診タイミング**: 事前（予約時/来院前）・来院時の両方対応
- **対応言語**: 日本語のみ

---

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| フロントエンド | React (TypeScript), Vite, Tailwind CSS |
| バックエンド | FastAPI (Python 3.12+) |
| データベース | PostgreSQL（メイン）, Redis（セッション/キャッシュ） |
| AI分析 | Claude API (Anthropic) |
| 認証 | QRコード + JWT |
| 電子カルテ連携 | HL7 FHIR R4 |
| コンテナ | Docker / Docker Compose |
| CI/CD | GitHub Actions |

---

## アーキテクチャ

```
患者（スマホ/タブレット）
        │ QRコード認証
        ▼
[ React SPA (フロントエンド) ]
        │ HTTPS (TLS)
        ▼
[ FastAPI (バックエンドAPI) ]
   ├── 問診フォームエンジン（動的分岐）
   ├── QRコード発行/検証
   ├── Claude API クライアント（AI分析）
   ├── FHIR クライアント（電子カルテ連携）
   └── PDF生成（reportlab/WeasyPrint）
        │
        ▼
[ PostgreSQL ] ← 暗号化済みデータ
[ Redis ]      ← セッション・QRトークン

        │ HL7 FHIR R4
        ▼
[ 電子カルテシステム (EHR) ]

医師用ダッシュボード（React SPA 内）
```

---

## 主要機能

### 1. QRコード認証フロー
- 予約時に患者固有のQRコードを発行（有効期限付き）
- 来院時にQRをスキャンして問診セッションを開始
- QRトークンはRedisで管理（TTL: 予約日 + 1日）
- 未使用のQRは自動失効

### 2. 診療科別問診フォーム
- 診療科ごとに完全に独立したフォーム定義
- フォーム定義はDBで管理（JSON Schema ベース）
- 管理者画面でフォームの追加・編集・公開が可能

### 3. 動的分岐ロジック
- 回答に応じて次の質問群が変化（条件分岐ツリー）
- 分岐ルールはフォーム定義にJSONで記述
- 例: 「胸の痛みがある → はい」→ 「痛みの程度・場所を追加質問」

### 4. AI分析・サマリー（Claude API）
- 患者の回答を受けてClaude APIが症状を要約
- 医師用に「主訴」「重要フラグ」「推奨確認事項」を生成
- プロンプトは安全性を最優先（診断は行わず情報整理のみ）
- API呼び出しは非同期（Celery or BackgroundTasks）

### 5. 医師用ダッシュボード
- 本日の予約患者一覧と問診完了状況
- 患者の問診回答全文 + AIサマリーを並べて表示
- 診療科・ステータスでフィルタリング

### 6. 電子カルテ連携（HL7 FHIR R4）
- 問診回答を `QuestionnaireResponse` リソースとしてFHIRサーバーに送信
- 患者IDは `Patient` リソースと紐付け
- エラー時はリトライキュー（Redis）で冗長化

### 7. PDF出力
- 問診票をA4 PDFに出力（印刷用）
- 患者氏名・受診日・診療科・全回答を含む
- 医師サイン欄あり

---

## データモデル（主要テーブル）

```sql
-- 診療科
departments (id, name, code, form_id, is_active)

-- フォーム定義（診療科ごと）
form_definitions (id, department_id, version, schema JSONB, is_published, created_at)

-- 患者（最小限の情報のみ保持）
patients (id, external_patient_id, name_encrypted, dob_encrypted, created_at)

-- 問診セッション
inquiry_sessions (
  id, patient_id, department_id, appointment_at,
  qr_token, status, started_at, completed_at
)

-- 問診回答
inquiry_responses (
  id, session_id, form_definition_id,
  answers JSONB,        -- 暗号化済み
  ai_summary TEXT,      -- 暗号化済み
  fhir_resource_id,
  created_at
)

-- ユーザー（病院スタッフ）
staff_users (id, email, role, department_ids[], is_active)

-- 監査ログ
audit_logs (id, staff_user_id, action, resource_type, resource_id, ip_address, created_at)
```

---

## セキュリティ要件

### 通信
- 全通信TLS 1.3必須（HTTP→HTTPSリダイレクト）
- CSRFトークン（Cookie + Header方式）
- CORS設定は許可オリジンのみ明示

### データ暗号化
- 患者の氏名・生年月日・回答内容はAES-256-GCMで暗号化してDB保存
- 暗号化キーはAWS KMS / HashiCorp Vault で管理（環境変数に平文キー禁止）

### アクセス制御（RBAC）
| ロール | 権限 |
|--------|------|
| `admin` | システム全体の設定、フォーム管理、スタッフ管理 |
| `doctor` | 担当診療科の問診回答・AIサマリー閲覧 |
| `nurse` | 担当診療科の問診完了状況確認（回答詳細は閲覧不可） |
| `reception` | QRコード発行、セッション開始操作 |

- JWTアクセストークン（有効期限15分）+ リフレッシュトークン（8時間）
- 不正ログイン試行は5回でアカウントロック

### 監査ログ
- 患者データへの全アクセスをaudit_logsテーブルに記録
- ログの改ざんを防ぐためにINSERT ONLYポリシー適用
- 保持期間: 5年

---

## API設計方針

- REST API（OpenAPI 3.1仕様書を必ず最初に定義）
- エンドポイントはリソース指向: `/api/v1/{resource}`
- レスポンスは統一フォーマット:
  ```json
  {
    "data": {...},
    "meta": {"request_id": "...", "timestamp": "..."},
    "error": null
  }
  ```
- エラーレスポンスはRFC 7807 (Problem Details) 準拠
- 全APIにリクエストIDを付与してトレーサビリティを確保

---

## ディレクトリ構成

```
claudeinquiry/
├── CLAUDE.md
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py          # 環境変数管理 (pydantic-settings)
│   │   │   ├── security.py        # 暗号化・JWT
│   │   │   └── database.py        # DB接続
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── sessions.py    # QRコード・問診セッション
│   │   │       ├── forms.py       # フォーム定義
│   │   │       ├── responses.py   # 問診回答
│   │   │       ├── dashboard.py   # 医師用
│   │   │       └── admin.py
│   │   ├── models/                # SQLAlchemy ORM
│   │   ├── schemas/               # Pydantic スキーマ
│   │   ├── services/
│   │   │   ├── ai_analysis.py     # Claude API連携
│   │   │   ├── fhir_client.py     # HL7 FHIR連携
│   │   │   ├── qr_service.py      # QRコード生成
│   │   │   └── pdf_service.py     # PDF生成
│   │   └── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── patient/           # 患者向け問診画面
│   │   │   ├── dashboard/         # 医師用ダッシュボード
│   │   │   └── admin/             # 管理者画面
│   │   ├── components/
│   │   │   ├── form-engine/       # 動的フォームレンダラー
│   │   │   └── ui/
│   │   ├── hooks/
│   │   ├── api/                   # APIクライアント (openapi-typescript-codegen)
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
└── docs/
    ├── requirements.md            # 要件定義書
    ├── db-definition.md           # DB定義書・ER図
    ├── screen-definition.md       # 画面定義書
    ├── api-specification.md       # API仕様書（人間可読版）
    ├── openapi.yaml               # API仕様書（OpenAPI 3.1 機械可読版。実装前に先に書く）
    ├── test-specification.md      # テスト仕様書
    ├── fhir-mapping.md            # FHIRリソースマッピング定義
    └── form-schema.md             # フォーム定義スキーマ仕様
```

---

## 開発規約

### 実装順序（必ず守ること）
1. `docs/openapi.yaml` を先に定義してからAPIを実装
2. テストはRed-Green-Refactorで書く（テストなしのコミット禁止）
3. セキュリティ関連（暗号化・認証）は最初に実装し、後付け禁止

### Python (FastAPI)
- 型ヒント必須（`mypy --strict` を通すこと）
- 非同期処理は `async/await` を使用
- SQLAlchemyは非同期セッション（`AsyncSession`）を使用
- 環境変数は `pydantic-settings` で一元管理（`.env`ファイルは`.gitignore`）

### TypeScript (React)
- `any` 型の使用禁止
- APIレスポンスの型はOpenAPI仕様から自動生成
- コンポーネントはFunctional Component のみ

### Claude API利用ルール
- 患者の個人識別情報（氏名・生年月日）はプロンプトに含めない
- プロンプトには「医療診断を行わないこと」を明示的に指示する
- APIコールはすべてログに記録（入出力トークン数・レイテンシ）
- レート制限対策としてリトライ（指数バックオフ）を実装

### テスト方針
- `backend/tests/` に全APIのintegrationテストを配置
- DBはテスト用の実際のPostgreSQLを使用（モックDB禁止）
- カバレッジ目標: バックエンド80%以上

---

## 環境変数（必須）

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/inquiry_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=<32バイト以上のランダム文字列>
ENCRYPTION_KEY=<AES-256用キー (KMS経由で取得)>

# Claude API
ANTHROPIC_API_KEY=<Anthropic APIキー>
CLAUDE_MODEL=claude-sonnet-4-6

# FHIR
FHIR_SERVER_URL=https://fhir.hospital.example.com/fhir/R4
FHIR_CLIENT_ID=<クライアントID>
FHIR_CLIENT_SECRET=<クライアントシークレット>

# App
ENVIRONMENT=development  # development | staging | production
ALLOWED_ORIGINS=https://inquiry.hospital.example.com
```

---

## 注意事項・制約

- **医療法・個人情報保護法準拠**: 患者データの保持期間・削除ポリシーは法務確認済みのものを実装
- **AI免責**: AIサマリーは「参考情報」として表示し、医師の判断を代替しない旨を画面に明示
- **オフライン対応**: タブレット端末での来院時問診は、一時的なネットワーク断でも回答が失われないようLocalStorageに一時保存する
- **アクセシビリティ**: 高齢患者が使用するため、フォントサイズ・タッチターゲットサイズはWCAG 2.1 AA準拠
