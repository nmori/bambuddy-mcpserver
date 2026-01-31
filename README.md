# Bambuddy MCP Server

Bambu Lab プリンター用の Model Context Protocol (MCP) サーバーです。Claude Code などの AI アシスタントから Bambu Lab 3D プリンターを操作できるようにします。

## 概要

このプロジェクトは、Bambu Lab の 3D プリンターと連携するための MCP サーバーを提供します。BambuConnect API 経由でプリンターの状態確認、ジョブ管理などが可能です。

## 機能

- **プリンター一覧取得**: 利用可能な Bambu Lab プリンターの一覧を取得
- **プリンター状態確認**: 特定プリンターの現在の状態（温度、進捗など）を取得
- **ジョブ一覧取得**: 印刷ジョブの一覧を取得
- **ジョブ詳細取得**: 特定ジョブの詳細情報を取得

## インストール

### 必要要件

- Python 3.10 以上
- pip または uv

### セットアップ

1. リポジトリをクローン:
```bash
git clone https://github.com/nmori/bambuddy-mcpserver.git
cd bambuddy-mcpserver
```

2. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

または、開発モードでインストール:
```bash
pip install -e .
```

## 設定

### 環境変数

以下の環境変数を設定してください:

- `BAMBU_CONNECT_URL`: BambuConnect API のベース URL（デフォルト: http://localhost:8080）
- `BAMBU_CONNECT_TOKEN`: BambuConnect API のアクセストークン（オプション）

`.env.example` ファイルを `.env` にコピーして設定を行うことができます:

```bash
cp .env.example .env
# .env ファイルを編集して適切な値を設定
```

### MCP クライアント設定

Claude Code などの MCP クライアントで使用する場合、`mcp_config.json` を参考に設定してください:

```json
{
  "mcpServers": {
    "bambuddy": {
      "command": "python",
      "args": ["-m", "bambuddy_mcpserver.server"],
      "env": {
        "BAMBU_CONNECT_URL": "http://localhost:8080",
        "BAMBU_CONNECT_TOKEN": "your_access_token_here"
      }
    }
  }
}
```

## 使用方法

### スタンドアロンで実行

```bash
python -m bambuddy_mcpserver.server
```

または、インストール済みの場合:

```bash
bambuddy-mcp
```

### MCP クライアントから使用

Claude Code や他の MCP 対応クライアントから、以下のツールが利用可能です:

#### get_printers
利用可能なプリンターの一覧を取得します。

```json
{
  "name": "get_printers",
  "arguments": {}
}
```

#### get_printer_status
特定プリンターの現在の状態を取得します。

```json
{
  "name": "get_printer_status",
  "arguments": {
    "device_id": "printer_device_id"
  }
}
```

#### get_print_jobs
印刷ジョブの一覧を取得します。

```json
{
  "name": "get_print_jobs",
  "arguments": {
    "device_id": "printer_device_id"  // オプション
  }
}
```

#### get_job_details
特定ジョブの詳細情報を取得します。

```json
{
  "name": "get_job_details",
  "arguments": {
    "job_id": "job_id"
  }
}
```

## 開発

### プロジェクト構造

```
bambuddy-mcpserver/
├── bambuddy_mcpserver/
│   ├── __init__.py       # パッケージ初期化
│   ├── client.py         # BambuConnect API クライアント
│   └── server.py         # MCP サーバー実装
├── .env.example          # 環境変数のサンプル
├── .gitignore           # Git 除外設定
├── mcp_config.json      # MCP クライアント設定サンプル
├── pyproject.toml       # プロジェクト設定
├── requirements.txt     # 依存関係
└── README.md           # このファイル
```

### 依存関係

- **mcp**: Model Context Protocol SDK
- **requests**: HTTP クライアント
- **pydantic**: データバリデーション

## トラブルシューティング

### BambuConnect に接続できない

- `BAMBU_CONNECT_URL` が正しく設定されているか確認してください
- BambuConnect サーバーが起動しているか確認してください
- ファイアウォール設定を確認してください

### 認証エラー

- `BAMBU_CONNECT_TOKEN` が正しく設定されているか確認してください
- トークンが期限切れでないか確認してください

## ライセンス

MIT License

## 貢献

Issue や Pull Request を歓迎します！

## 関連リンク

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Bambu Lab](https://bambulab.com/)
