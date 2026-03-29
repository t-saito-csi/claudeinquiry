# 問診システム (Medical Inquiry System)

大規模病院向けのデジタル問診システム。患者が来院前または来院時にスマートフォン/タブレットで問診票を記入し、医師が診察前に情報を把握できる。

## 技術スタック

| レイヤー | 技術 |
|---|---|
| フロントエンド | React (TypeScript), Vite, Tailwind CSS |
| バックエンド | FastAPI (Python 3.12+) |
| データベース | PostgreSQL 16 |
| キャッシュ/セッション | Redis 7 |
| AI分析 | Claude API (Anthropic) |
| 電子カルテ連携 | HL7 FHIR R4 |

## 必要要件

- Docker 24.0 以上
- Docker Compose v2.20 以上
- Git

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd claudeinquiry
```

### 2. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を開き、以下の値を必ず変更してください。

| 変数 | 説明 | 生成コマンド |
|---|---|---|
| `SECRET_KEY` | JWT署名キー (32バイト以上) | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | AES-256-GCM暗号化キー | `openssl rand -base64 32` |
| `ANTHROPIC_API_KEY` | Anthropic APIキー | [Anthropic Console](https://console.anthropic.com) で取得 |

開発環境ではその他の値はデフォルトのまま使用できます。

### 3. 開発環境の起動

```bash
docker compose up --build
```

初回はイメージのビルドがあるため数分かかります。

サービスが起動したら以下のURLでアクセスできます。

| サービス | URL |
|---|---|
| フロントエンド | http://localhost:5173 |
| バックエンドAPI | http://localhost:8000 |
| API ドキュメント (Swagger) | http://localhost:8000/docs |
| API ドキュメント (ReDoc) | http://localhost:8000/redoc |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## 開発コマンド一覧

```bash
# 開発環境の起動 (フォアグラウンド)
docker compose up

# 開発環境の起動 (バックグラウンド)
docker compose up -d

# 特定サービスのみ起動
docker compose up api db redis

# コンテナのログを確認
docker compose logs -f api
docker compose logs -f frontend

# コンテナを停止
docker compose down

# コンテナ・ボリュームをすべて削除 (DBデータも削除されます)
docker compose down -v

# イメージを再ビルドして起動
docker compose up --build

# バックエンドコンテナ内でコマンドを実行
docker compose exec api bash

# DBマイグレーション実行 (Alembic)
docker compose exec api alembic upgrade head

# バックエンドのテスト実行
docker compose exec api pytest

# フロントエンドコンテナ内でコマンドを実行
docker compose exec frontend sh
```

## 本番環境へのデプロイ

```bash
# 本番用設定で起動
docker compose -f docker-compose.prod.yml up -d

# 本番用ビルド (APIエンドポイントを指定)
VITE_API_URL=https://api.hospital.example.com docker compose -f docker-compose.prod.yml up --build -d
```

本番環境では以下を必ず確認してください。

- `SECRET_KEY` および `ENCRYPTION_KEY` に安全なランダム値を設定
- `REDIS_PASSWORD` を設定
- `ALLOWED_ORIGINS` を本番ドメインに変更
- `ENVIRONMENT=production` を設定
- 暗号化キーは環境変数の平文ではなく KMS / HashiCorp Vault 経由で管理

## 環境変数の説明

`.env.example` を参照してください。

## ディレクトリ構成

```
claudeinquiry/
├── docker-compose.yml        # 開発環境
├── docker-compose.prod.yml   # 本番環境
├── .env.example              # 環境変数テンプレート
├── backend/                  # FastAPI アプリケーション
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
├── frontend/                 # React アプリケーション
│   ├── Dockerfile
│   ├── nginx.conf            # 本番用 nginx 設定
│   └── src/
└── docs/                     # 設計ドキュメント
```

## トラブルシューティング

**ポートが競合している場合**

```bash
# 使用中のポートを確認
lsof -i :8000
lsof -i :5173
lsof -i :5432
```

**DBに接続できない場合**

```bash
# DBコンテナの状態を確認
docker compose ps db
docker compose logs db
```

**依存パッケージを更新した場合**

```bash
# イメージを再ビルド
docker compose build api
docker compose build frontend
```
