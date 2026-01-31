# bambuddy-mcpserver
Bambuddy 用の MCP サーバです。Claude などの MCP クライアントから、Bambu Lab 3D プリンタの状態確認や印刷キュー操作を行えます。

## できること
- プリンタの一覧・状態確認
- 印刷の一時停止/再開/停止、チャンバーライト操作
- 印刷キューの確認・追加・キャンセル・削除
- 印刷履歴（アーカイブ）の検索/統計/更新
- フィラメント在庫の確認・追加
- メンテナンス状況の確認
- ライブラリ/プリンタ内ファイルの閲覧

## 前提条件
- Bambuddy サーバが稼働していること
- Python 環境（推奨: 3.10+）

## セットアップ
1. 依存関係をインストール
	 - requirements-mcp.txt を使ってインストールしてください。
2. 環境変数を設定
	 - BAMBUDDY_URL: Bambuddy の URL（例: http://localhost:8000）
	 - BAMBUDDY_API_KEY: API キー（認証が必要な場合のみ）

## 起動方法
標準入出力（stdio）で MCP サーバを起動します。

- Python 実行例: `python -m mcp_server.server`

## Claude Desktop での利用
claude_desktop_config.json が同梱されています。以下を実環境に合わせて置き換えてください。

- command: Python 実行ファイルのフルパス
- PYTHONPATH: このリポジトリのパス
- BAMBUDDY_URL / BAMBUDDY_API_KEY: 接続先情報

例:
```
{
	"mcpServers": {
		"bambuddy": {
			"command": "C:\\Path\\To\\python.exe",
			"args": ["-m", "mcp_server.server"],
			"env": {
				"BAMBUDDY_URL": "http://localhost:8000",
				"BAMBUDDY_API_KEY": "<your_api_key>",
				"PYTHONPATH": "D:\\application\\bambuddy-mcpserver"
			}
		}
	}
}
```

## MCP ツール一覧（主要）
まず `list_printers` を実行してプリンタ ID を取得してください。

- `list_printers`：プリンタ一覧
- `get_printer_status(printer_id)`：詳細ステータス
- `get_system_info`：Bambuddy システム情報
- `pause_print(printer_id)` / `resume_print(printer_id)` / `stop_print(printer_id)`：印刷操作
- `set_chamber_light(printer_id, on)`：チャンバーライト操作
- `list_print_queue(printer_id?, status?)`：印刷キュー一覧
- `add_to_print_queue(...)`：印刷キュー追加
- `cancel_queue_item(item_id)` / `delete_queue_item(item_id)`：キュー操作
- `list_archives(printer_id?, limit?, offset?)`：印刷履歴一覧
- `search_archives(q, printer_id?, status?, limit?)`：履歴検索
- `get_archive_stats()`：集計統計
- `update_archive(archive_id, ...)`：履歴メタ情報更新
- `list_filaments()` / `add_filament(...)`：フィラメント在庫
- `get_maintenance_overview()` / `get_printer_maintenance(printer_id)`：メンテナンス
- `list_library_files(folder_id?, limit?, offset?)`：ライブラリ一覧
- `list_printer_files(printer_id, path)`：プリンタ内ファイル一覧
- `get_settings()`：Bambuddy 設定

## MCP リソース
- bambuddy://printers
- bambuddy://printers/{printer_id}/status
- bambuddy://stats
- bambuddy://system

## よくある流れ（例）
1. `list_printers` で ID を取得
2. `get_printer_status(printer_id)` で状態確認
3. `list_library_files` or `search_archives` で印刷対象を探す
4. `add_to_print_queue` で印刷キューに追加

## トラブルシューティング
- 接続できない場合: `BAMBUDDY_URL` が正しいか、Bambuddy が起動しているか確認してください。
- 認証エラー: `BAMBUDDY_API_KEY` を設定してください。
