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

# ファイルのエンコーディングをチェック（非UTF-8とBOM問題を検出）
polydrive i18n check-encoding examples/bad_encoding/ --require-utf8 --fail-on-bom

# C/C++ソースコード内のハードコードされたCJK文字列を検出
polydrive i18n detect-hardcoded examples/cpp_project/ --lang cpp

# 多言語用語集をインポート
polydrive glossary import examples/automotive_terms.csv

# 疑似ローカライズされたリソースを生成
polydrive i18n pseudo-localize examples/locales/en.json --mode expand+cjk

# 欠陥レポートを分析
polydrive defect analyze --input examples/bug_report_zh.json

# REST APIサーバーを起動
polydrive serve --port 8080
```

詳しくは [examples/README.md](examples/README.md) をご覧ください。

## デモ

以下のすべてのコマンドは、バンドルされた `examples/` データに対して実行したものです。出力は読みやすさのために省略しています — Rich レンダリングされた完全なテーブルを確認するには、ぜひご自身で実行してみてください。

**エンコーディングガード** — 多言語 CI パイプラインを破壊する前に、非 UTF-8 ファイルと BOM マーカーをフラグ付けします:

```
$ polydrive i18n check-encoding examples/bad_encoding/ --require-utf8 --fail-on-bom

                   Encoding Issues in examples/bad_encoding/
┌────────────────────┬──────┬──────────┬───────────┬──────────────────────┐
│ File               │ Line │ Type     │ Detected  │ Details              │
├────────────────────┼──────┼──────────┼───────────┼──────────────────────┤
│ gb2312_file.cpp    │    - │ non_utf8 │ gb18030   │ File is gb18030...   │
│ shift_jis_file.cpp │    - │ non_utf8 │ cp932     │ File is cp932...     │
│ utf8_with_bom.cpp  │    - │ has_bom  │ utf-8-sig │ File contains a BOM  │
└────────────────────┴──────┴──────────┴───────────┴──────────────────────┘
```

**ハードコード文字列の検出** — i18n リソースに存在すべき CJK リテラルが C/C++ ソースに埋め込まれているのを見つけ出します:

```
$ polydrive i18n detect-hardcoded examples/cpp_project/ --lang cpp

                  Hardcoded Strings in examples/cpp_project/
┌────────────────────────┬──────┬─────┬──────────────────────────────┐
│ File                   │ Line │ Col │ Text                         │
├────────────────────────┼──────┼─────┼──────────────────────────────┤
│ dashboard.cpp          │    8 │   7 │ 制动液位过低，请及时补充     │
│ dashboard.cpp          │   10 │  30 │ 制动系统故障，请立即停车检查 │
│ instrument_cluster.cpp │    6 │   7 │ 点検時期が過ぎています       │
│ ...                    │      │     │ (9 hardcoded strings total)  │
└────────────────────────┴──────┴─────┴──────────────────────────────┘
```

**欠陥レポート品質** — 言語が混在するバグレポートをスコアリングし、欠けている要素を浮き彫りにします:

```
$ polydrive defect analyze --input examples/bug_report_zh.json

Defect report BUG-2024-0158  severity: info  composite score: 76.6
        Quality Breakdown
┌────────────────────────┬───────┐
│ Dimension              │ Score │
├────────────────────────┼───────┤
│ Field completeness     │  87.5 │
│ Text quality           │  51.4 │
│ Reproducibility        │  75.0 │
│ Terminology compliance │ 100.0 │
└────────────────────────┴───────┘
Detected language: no
⚠ Language mixing detected: 48% non-dominant script (dominant: cjk)
Missing fields: environment
Suggestions:
  • Add environment details (OS, version, platform, etc.)
  • Description is a single sentence — add more detail
```

**疑似ローカライズ** — 本番の翻訳が届く前に、HMI レイアウトをストレステストします。`"Engine Temperature"` → `"[Êñ夕ïñê 七ê山巳ê尺ä七û尺ê -------]"`（expand+cjk モード）、`examples/locales/en.pseudo.json` に出力されます。

## スクリーンショット

`polydrive defect analyze` が同梱の中/独混在欠陥レポート（`examples/bug_report_zh.json`）をスコアリングした結果の可視化です。以下の各値はモックではなく、実際の実行に基づきます：

![欠陥品質スコアカード](docs/defect-quality-chart.svg)

各コマンドの完全な Rich レンダリング済みテーブルは、上記の[デモ](#デモ)セクションをご覧ください。独自のデモ GIF を録画するには：

```bash
# ターミナルセッションを録画し、GIF に変換（asciinema + agg が必要）
asciinema rec demo.cast --command "polydrive defect analyze --input examples/bug_report_zh.json"
agg demo.cast demo.gif
```

## その他のコマンド

```bash
# 用語の一貫性をチェック（TBXフォーマットが必要）
polydrive glossary check terms.tbx --lang-pair en:zh

# 用語適用による翻訳
polydrive mt translate --text "Bremsfehler erkannt" --from de --to en --glossary terms.tbx

# Qt翻訳ファイルを検証
polydrive i18n validate-qt translations/app_zh_CN.ts

# 言語間でのGherkinフィーチャー同期をチェック
polydrive trace sync-gherkin --base en --compare zh,de --features tests/

# UNECE R121 HMIコンプライアンスをチェック
polydrive trace unece-check --manifest hmi_manifest.json

# ASPICE言語関連エビデンスを収集
polydrive trace aspice-evidence --project .

# 品質メトリクスを表示
polydrive metrics summary --input metrics.json
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

## CI 連携

PolyDrive は、i18n チェックを PR ゲートとして実行する再利用可能な GitHub Action を同梱しています：

```yaml
- uses: BUNSEI1212/polydrive/.github/actions/i18n-check@v0.1.0
  with:
    path: src
    # install-command のデフォルトは `pip install polydrive`。
    # ソースチェックアウトの場合は例えば `pip install -e .` を使用します
```

`check-encoding`（`--require-utf8 --fail-on-bom` 付き）を実行し、C/C++ ソースが存在する場合は `detect-hardcoded` も実行します。いずれも問題を検出すると非ゼロで終了するため、単一のチェックでマージをブロックできます。このリポジトリは `.github/workflows/i18n-guard.yml` でこの Action をドッグフードしています。

## インパクトとロードマップ

### 誰が痛みを抱えているか

PolyDrive が対象とするのは、多国籍自動車**テストチーム**が日常的に直面する摩擦であり、翻訳チーム単独の課題ではありません:

- **分散したテストセル**（DE/CN/JP/US）は各母国語で欠陥を起票しますが、受け手のチームは翻訳によって説明がドリフトしたバグを再現しなければなりません。PolyDrive の `defect` モジュールは再現性をスコアリングし、言語混在をフラグ付けすることで、トリアージ前にギャップを可視化します。
- **HMI ホモロゲーション**は地域ごとのテルテール/インジケーター規則を満たす必要があります。`trace` は UNECE R121 コンプライアンスをチェックし、手作業の監査スプレッドシートの代わりに ASPICE の言語エビデンスを一回のパスで収集します。
- **CI パイプライン**は、Shift-JIS や GB2312 のソースファイルが UTF-8 ツールチェーンに紛れ込むとサイレントに破綻します。`i18n check-encoding` はこれを高速で明白な失敗に変えます。
- **用語ドリフト** は、要件 → テスト → 欠陥の間でトレーサビリティを蝕みます。`glossary` は言語をまたいで一つの正規用語セットを維持します。

PolyDrive は意図的に範囲を絞り、オープンです。用語、欠陥品質、i18n ガード、トレーサビリティを CI ステップに収まる一つの CLI で結びつけます。これは既存ツールの多くがスプレッドシートや専用スクリプトに任せているギャップです。

### ロードマップ

PolyDrive は若いプロジェクト（0.x）です。以下は計画中の方向性であり、対応が始まると GitHub Issues で追跡されます:

- **さらなる規格**: ISO 26262 安全用語、ISO/SAE 21434 サイバーセキュリティ用語、AUTOSAR ARXML 抽出、ISO 9241 HMI エルゴノミクスチェック。
- **翻訳品質**: `mt` ゲートウェイ上での MQM/DAQP エラー分類スコアリング（単なるパススルー翻訳にとどまらない）。
- **自動化**: 既存の欠陥/テストコーパスからの用語抽出による用語集のブートストラップ、そしてすべてのチェックを PR で実行するファーストクラスの GitHub Action。
- **エコシステム**: 用語とハードコード文字列の警告をコミット後ではなく記述中に表示する、言語サーバー / IDE 統合。
- **リーチ**: さらなる BCP 47 ロケールと、既存 REST API の上に構築した Web UI。

BSL → Apache 2.0 変換（リリースごとに36ヶ月）により、初期の商用利用がメンテナンスを支える一方で、長期的な末尾は完全にオープンであり続けます。

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

## メンテナンスとガバナンス

PolyDrive は現在 **単独メンテナ** が保守しています。この規模で持続可能であり続けるため、ワークフローは意図的にツール支援型でプロセス軽量にしています:

- **イシュートリアージ** — バグと機能要望は [GitHub Issues](https://github.com/BUNSEI1212/polydrive/issues) に集められ、モジュール（`glossary`, `i18n`, `defect`, …）と種別（`bug`, `enhancement`, `standard`）でラベル付けされます。明確な再現手順（入力ファイル + コマンド + 期待値と実績値）があるものがキューの先頭に進みます。
- **機能計画** — より大きな作業は [ロードマップ](#インパクトとロードマップ) に照らしてスコープし、コード着手前にマイルストーンで追跡することで範囲を境界づけます。アイデアはまず `discussion` タグのイシューで提案してください。
- **ツールの活用** — メンテナは自動化を活用して作業を増幅します。CI マトリクスがプラットフォームリグレッションを検出し、`ruff` + `pytest` がすべての変更でスタイルと挙動を守り、PolyDrive 自身も [dogfooded](https://en.wikipedia.org/wiki/Eating_your_own_dog_food) されています — 同梱の examples に対して独自の CLI チェックが統合テスト（`tests/test_examples.py`）として実行され、さらに再利用可能な GitHub Action としてすべての PR でゲート（`.github/workflows/i18n-guard.yml`）されています。AI 支援による開発がルーチンのリファクタリングとテスト足場を扱うことで、レビューは設計に集中できます。
- **リリース** — semver に従ってバージョン管理。BSL 変更日メカニズムが各リリースを36ヶ月後に Apache 2.0 に変換し、プロジェクトが進化しても古いバージョンが使い続けられるようにします。

貢献は歓迎します — [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。商用利用やカスタムの変更日については、ライセンスについて議論するためのイシューを開いてください。

## メンテナとしての私の役割

私は PolyDrive の単独メンテナであり、アーキテクチャ・実装・レビュー・リリースまで全ライフサイクルを担当しています。ワークフローは一人の人間に最適化されています:

- **単独開発** — 6つのモジュールすべてについて私自身が設計と実装を行い、一人の人間がシステム全体を頭に入れられるよう、APIの表面積を小さく一貫させます。レビューが私一人であっても、すべての変更はブランチ + プルリクエストで進め、履歴が監査可能な状態を保ちます。
- **バグ修正は証拠ファースト** — 何かが壊れたらまず再現し、コードに触れる前に根本原因を突き止め、回帰テストを追加します。最近の例：`defect analyze` がテキストモードで何も出力しない件 (#6)、`detect-hardcoded` が検出結果があったのに終了コード 0 を返す件 — これが CI ゲートを無力化する恐れがありました (#7)。いずれもテストファーストで修正しました（RED → GREEN）。
- **機能計画** — [Roadmap](#インパクトとロードマップ) が優先順位を決定します。より大きな作業は、コードを書き始める前にコンテキスト・未解決の疑問点・受け入れ基準を備えた追跡対象の GitHub イシューになります（例：#3、#5）。トリアージコメントで優先度と目標マイルストーンを設定します。
- **自動化をテコにする** — 単独メンテナが手作業でレビューすることはできないため、ツールに任せます：すべての変更で `ruff` + `pytest`、プラットフォーム網羅のための CI マトリクス、そしてすべての PR で PolyDrive 自身のチェックをドッグフードする再利用可能な GitHub Action です。PolyDrive は自身の examples をチェックします。
- **AI 支援による開発** — 私は AI（Claude Code）をルーティンワークの加速に使います：テストのドラフト、リファクタリング、コードベースの探索、ドキュメントの作成です。レビュアーは私のままです：マージ前にすべての変更を実際のコマンド出力とテストで検証し、コミットメッセージでは AI の共著を明記します。AI は私のリーチを広げますが、私の判断を置き換えるものではありません。
- **リリース** — semver タグに BSL → Apache 2.0 の変更日を併用し、古いバージョンが使い続けられるようにします。`v0.1.0` をリリース済みです。

私がこのプロジェクトを保守する理由は、このギャップ — 多国籍自動車テスト向けに用語、欠陥品質、i18n、トレーサビリティを結びつけること — が、既存のオープンソースではうまく満たされていないからです。

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
