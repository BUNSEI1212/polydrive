# PolyDrive

[![CI](https://github.com/BUNSEI1212/polydrive/actions/workflows/test.yml/badge.svg)](https://github.com/BUNSEI1212/polydrive/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-BSL%201.1-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

**[English](README.md)** | [中文](README.zh-CN.md) | 日本語

> 多国籍自動車テストチームのための言語ガバナンスツールキット

PolyDriveは、テストワークフローにおける言語関連の摩擦を**可視化・定量化・アクション可能**にするCLIファーストのツールキットです。用語一貫性チェック、欠陥レポート品質分析、国際化（i18n）ガード、翻訳オーケストレーション、コンプライアンストレーサビリティを統合的にサポートします。

## なぜ PolyDrive が必要か

多国籍の自動車テストにおいて、言語は「翻訳効率」の問題ではありません。言語は**欠陥増幅器**であり、以下の側面に深刻な影響を与えます。

- **要件のトレーサビリティ** — 用語が言語間でドリフトし、要件追跡が破綻する
- **欠陥の再現率** — 翻訳によって説明のニュアンスが失われ、再現手順が不明瞭になる
- **CIパイプライン** — エンコーディング問題がゴーストバグ（実在しないバグ）を引き起こす
- **コンプライアンス** — HMIテキストが地域の言語規制を満たさない

このギャップを解決するオープンソースツールはこれまで存在しませんでした。PolyDriveがその解決策です。既存のツールは部分的な解決にとどまりますが、自動車テストワークフローに特化して用語管理、欠陥品質、i18nチェック、トレーサビリティを統合的に結びつけるオープンソースツールはほぼ存在しません。

## 6つのモジュール

| モジュール | CLIコマンド | 機能 |
|--------|-------------|---------|
| 用語エンジン (glossary) | `polydrive glossary` | TBX/CSV用語インポート、一貫性チェック、エクスポート |
| 国際化ガード (i18n) | `polydrive i18n` | エンコーディングチェック、ハードコードCJK検出、疑似ローカライズ、Qt検証 |
| 欠陥品質 (defect) | `polydrive defect` | 欠陥レポート品質スコア、テンプレート検証、言語検出 |
| 翻訳オーケストレーション (mt) | `polydrive mt` | マルチエンジン翻訳 + 用語注入 + キャッシュ |
| トレーサビリティ (trace) | `polydrive trace` | Gherkin多言語同期、UNECE R121コンプライアンス、ASPICEエビデンス |
| 品質メトリクス (metrics) | `polydrive metrics` | 品質指標サマリー、Prometheusエクスポート、HTMLレポート |

さらに、`polydrive serve` でREST APIサーバーを起動できます。

## クイックスタート

```bash
# ソースからインストール
git clone https://github.com/BUNSEI1212/polydrive.git
cd polydrive
pip install -e .

# またはPyPIからインストール（公開後）
# pip install polydrive

# ファイルのエンコーディングをチェック
polydrive i18n check-encoding examples/bad_encoding/ --require-utf8

# C/C++ソースコード内のハードコードされたCJK文字列を検出
polydrive i18n detect-hardcoded examples/cpp_project/ --lang cpp

# TBX用語集をインポート
polydrive glossary import examples/automotive_terms.csv

# 用語の一貫性をチェック（TBXフォーマットが必要）
# polydrive glossary check terms.tbx --lang-pair en:zh

# 疑似ローカライズされたリソースを生成
polydrive i18n pseudo-localize examples/locales/en.json --mode expand+cjk

# 欠陥レポートを分析
polydrive defect analyze --input examples/bug_report_zh.json

# Qt翻訳ファイルを検証
polydrive i18n validate-qt translations/app_zh_CN.ts

# 用語適用による翻訳
polydrive mt translate --text "Bremsfehler erkannt" --from de --to en --glossary terms.tbx

# 言語間でのGherkinフィーチャー同期をチェック
polydrive trace sync-gherkin --base en --compare zh,de --features tests/

# UNECE R121 HMIコンプライアンスをチェック
polydrive trace unece-check --manifest hmi_manifest.json

# ASPICE言語関連エビデンスを収集
polydrive trace aspice-evidence --project .

# 品質メトリクスを表示
polydrive metrics summary --input metrics.json

# REST APIサーバーを起動
polydrive serve --port 8080
```

## アーキテクチャ

```
┌──────────────────────────────────────────────────────────────┐
│                    PolyDrive プラットフォーム                     │
├──────────┬──────────┬──────────┬───────────┬─────────────────┤
│ glossary │ defect   │ i18n     │ mt        │ trace / metrics │
│ 用語エンジン│ 欠陥品質   │ 国際化守衛 │ 翻訳オーケストレ│ トレース / 度量    │
├──────────┴──────────┴──────────┴───────────┴─────────────────┤
│        core (用語管理 / エンコーディング / データモデル)          │
├──────────────────────────────────────────────────────────────┤
│   CLI (Typer)   │   API (FastAPI)   │   プラグイン             │
└──────────────────────────────────────────────────────────────┘
```

## サポート規格

- **TBX (ISO 30042)** — 用語交換フォーマット
- **TMX** — 翻訳メモリ交換フォーマット
- **BCP 47** — 言語タグ識別（RFC 5646）
- **Automotive SPICE 4.0** — プロセスコンプライアンスエビデンス（SWE.1–SWE.6、MAN.6）
- **UNECE R121** — HMI警告インジケーター・表示要件
- **Gherkin** — 多言語BDDシナリオ管理（70以上の言語対応）

## 開発

```bash
git clone https://github.com/BUNSEI1212/polydrive.git
cd polydrive

# 開発依存関係を含めてインストール
pip install -e ".[dev]"

# テストを実行
python -m pytest -v

# リント
ruff check .
ruff format --check .
```

## ライセンス

PolyDriveは **Business Source License 1.1 (BSL 1.1)** で提供されています。

- **非商用利用**：無料（学術研究、個人利用、オープンソースプロジェクト）
- **商用利用**：商用ライセンスが必要
- **変更日**：各バージョンはリリース後36ヶ月で **Apache License 2.0** に自動的に変換されます

詳細は [LICENSE](LICENSE) を参照してください。

## ML拡張機能（オプション）

`pip install polydrive[ml]` で、機械学習ベースの拡張機能が有効になります。以下のライブラリが追加でインストールされます。

- **spaCy** — 自然言語処理パイプライン
- **sentence-transformers** — セマンティック埋め込み生成
- **KeyBERT** — キーワード・用語の自動抽出

対応機能：

- Gherkin多言語セマンティックマッチング
- 欠陥テキストのNLP品質分析
- 要件・仕様書からの用語自動抽出

## 設定

PolyDriveはYAMLベースの設定ファイル（`.polydrive.yaml`）をサポートしています。

```bash
# 現在の設定を表示
polydrive config show

# デフォルト設定ファイルをカレントディレクトリに生成
polydrive config init
```

設定ファイルの検索順序：カレントディレクトリ → ホームディレクトリ（`~/.polydrive.yaml`）。ファイルが見つからない場合はデフォルト値が使用されます。

## APIサービス

`polydrive serve` でFastAPIベースのREST APIサーバーを起動できます。全モジュールの機能に対応する15のエンドポイントが提供されます。

```bash
# APIサーバーを起動（デフォルトポート: 8080）
polydrive serve --port 8080
```

起動後、`http://localhost:8080/docs` でSwagger UIによるAPIドキュメントを参照できます。
