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

### 3. Import and Check Terminology

```bash
polydrive glossary import examples/automotive_terms.csv
polydrive glossary check examples/automotive_terms.csv --lang-pair en:zh
```

### 4. Analyze a Defect Report

```bash
polydrive defect analyze --input examples/bug_report_zh.json
```

Evaluates a Chinese-language defect report for cross-language quality, completeness, and terminology consistency.

### 5. Generate Pseudo-Localized Resources

```bash
polydrive i18n pseudo-localize examples/locales/en.json --mode expand+cjk
```

---

## Demo 数据说明 / Demo Data Notes / デモデータの説明

### bug_report_zh.json
一份真实风格的中文缺陷报告，包含混合语言（中/英/德），用于演示跨语种缺陷质量分析。

### automotive_terms.csv
车载领域多语种术语表（英/中/德/日），包含技术术语、法规术语和缩写词。

### bad_encoding/
包含各种编码问题的 C++ 文件：Shift-JIS、GB2312、UTF-8 with BOM。

### cpp_project/
包含硬编码中日文字符串的 C++ 源文件，用于演示 i18n 守卫检测能力。

### locales/en.json
英文 HMI 本地化资源文件，用于演示伪本地化生成。
