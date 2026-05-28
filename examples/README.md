# PolyDrive Examples

Runnable demo data for PolyDrive CLI commands.

## Quick Demos

### 1. Check File Encodings

```bash
polydrive i18n check-encoding examples/bad_encoding/ --require-utf8
```

Detects encoding mismatches, BOM markers, and non-UTF-8 files.

### 2. Detect Hardcoded Strings in C/C++

```bash
polydrive i18n detect-hardcoded examples/cpp_project/ --lang cpp
```

Finds hardcoded CJK string literals that should be externalized to i18n resources.

### 3. Import Terminology

```bash
polydrive glossary import examples/automotive_terms.csv
```

Imports a multilingual automotive glossary (en/zh/de/ja) with 10 terms across technical, regulatory, and abbreviation categories.

### 4. Analyze a Defect Report

```bash
polydrive defect analyze --input examples/bug_report_zh.json
```

Evaluates a Chinese-language defect report for cross-language quality, completeness, and terminology consistency.

### 5. Generate Pseudo-Localized Resources

```bash
polydrive i18n pseudo-localize examples/locales/en.json --mode expand+cjk
```

### 6. Start REST API Server

```bash
polydrive serve --port 8080
```

Starts the FastAPI server. Visit `http://localhost:8080/docs` for the interactive API documentation.

---

## Demo Data Notes / Demo 数据说明 / デモデータの説明

### bug_report_zh.json
A realistic Chinese automotive defect report with mixed languages (zh/en/de), demonstrating cross-language defect quality analysis.

一份真实风格的中文缺陷报告，包含混合语言（中/英/德），用于演示跨语种缺陷质量分析。

中国語の自動車欠陥レポート。複数言語（中/英/独）が混在しており、クロスランゲージ品質分析のデモ用。

### automotive_terms.csv
Multilingual automotive glossary (en/zh/de/ja) with 10 terms. Format: `id,source_term,source_lang,target_term,target_lang,category,definition,note`.

车载领域多语种术语表（英/中/德/日），包含 10 个术语，涵盖技术术语、法规术语和缩写词。

自動車分野の多言語用語集（英/中/独/日）。10用語、技術/規制/略語カテゴリ。

### bad_encoding/
C++ files with various encoding issues: Shift-JIS, GB2312, UTF-8 with BOM.

包含各种编码问题的 C++ 文件：Shift-JIS、GB2312、UTF-8 with BOM。

各種エンコーディング問題を含むC++ファイル：Shift-JIS、GB2312、UTF-8 BOM付き。

### cpp_project/
C++ source files with hardcoded Chinese and Japanese strings, demonstrating i18n guard detection.

包含硬编码中日文字符串的 C++ 源文件，用于演示 i18n 守卫检测能力。

ハードコードされた中日文字列を含むC++ソースファイル。i18nガードの検出デモ用。

### locales/en.json
English HMI localization resource for pseudo-localization demo.

英文 HMI 本地化资源文件，用于演示伪本地化生成。

疑似ローカライズ生成デモ用の英語HMIローカライズリソース。
