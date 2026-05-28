# PolyDrive

[![CI](https://github.com/BUNSEI1212/polydrive/actions/workflows/test.yml/badge.svg)](https://github.com/BUNSEI1212/polydrive/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-BSL%201.1-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

**[English](README.md)** | **[中文](README.zh-CN.md)** | [日本語](README.ja.md)

> 跨国车载测试团队的语言治理工具包

PolyDrive 让测试工作流中的语言摩擦变得**可见、可量化、可行动**。这是一个 CLI 优先的工具包，涵盖术语一致性、缺陷质量、国际化守卫、翻译编排以及合规追溯。

## 为什么需要 PolyDrive

在跨国车载测试中，语言不仅是"翻译效率"问题——它是**缺陷放大器**，直接影响：

- **需求追溯性**：术语在跨语言传递过程中发生漂移，导致需求与实现脱节
- **缺陷复现率**：缺陷描述在翻译中丢失关键语义，测试人员无法准确复现问题
- **CI 管道**：编码问题引入幽灵 bug，构建在一种语言环境下通过、在另一种环境下崩溃
- **合规性**：HMI 文本不符合目标市场的地区法规要求，引发认证风险

现有工具解决了部分问题，但很少有开源工具专门针对汽车测试工作流，将术语管理、缺陷质量、i18n 检查和追溯性连接起来。PolyDrive 填补了这一空白。

## 六大模块

| 模块 | CLI 命令 | 功能 |
|--------|-------------|---------|
| 术语引擎 (glossary) | `polydrive glossary` | TBX/CSV 术语导入、一致性检查、导出 |
| 国际化守卫 (i18n) | `polydrive i18n` | 编码校验、硬编码 CJK 检测、伪本地化、Qt 验证 |
| 缺陷质检 (defect) | `polydrive defect` | 缺陷报告质量评分、模板验证、语言检测 |
| 翻译编排 (mt) | `polydrive mt` | 多引擎翻译 + 术语注入 + 缓存 |
| 追溯引擎 (trace) | `polydrive trace` | Gherkin 多语言同步、UNECE R121 合规、ASPICE 证据 |
| 质量度量 (metrics) | `polydrive metrics` | 质量指标汇总、Prometheus 导出、HTML 报告 |

另提供 `polydrive serve` 用于启动 REST API 服务。

## 快速开始

```bash
# 从源码安装
git clone https://github.com/BUNSEI1212/polydrive.git
cd polydrive
pip install -e .

# 或从 PyPI 安装（发布后可用）
# pip install polydrive

# 检查文件编码
polydrive i18n check-encoding examples/bad_encoding/ --require-utf8

# 检测 C/C++ 源码中的硬编码 CJK 字符
polydrive i18n detect-hardcoded examples/cpp_project/ --lang cpp

# 导入 TBX 术语表
polydrive glossary import examples/automotive_terms.csv

# 检查术语一致性（需要 TBX 格式）
# polydrive glossary check terms.tbx --lang-pair en:zh

# 生成伪本地化资源
polydrive i18n pseudo-localize examples/locales/en.json --mode expand+cjk

# 分析缺陷报告质量
polydrive defect analyze --input examples/bug_report_zh.json

# 验证 Qt 翻译文件
polydrive i18n validate-qt translations/app_zh_CN.ts

# 带术语约束的翻译（德语 -> 英语）
polydrive mt translate --text "Bremsfehler erkannt" --from de --to en --glossary terms.tbx

# 检查 Gherkin 跨语言场景同步
polydrive trace sync-gherkin --base en --compare zh,de --features tests/

# 检查 UNECE R121 HMI 合规性
polydrive trace unece-check --manifest hmi_manifest.json

# 收集 ASPICE 语言合规证据
polydrive trace aspice-evidence --project .

# 查看质量度量摘要
polydrive metrics summary --input metrics.json

# 启动 REST API 服务
polydrive serve --port 8080
```

## 架构

```
┌──────────────────────────────────────────────────────────────┐
│                      PolyDrive 平台                          │
├──────────┬──────────┬──────────┬───────────┬─────────────────┤
│ glossary │ defect   │ i18n     │ mt        │ trace / metrics │
│ 术语引擎  │ 质检器    │ 国际化守卫 │ 翻译编排   │ 追溯 / 度量     │
├──────────┴──────────┴──────────┴───────────┴─────────────────┤
│            核心层（术语库 / 编码处理 / 数据模型）                │
├──────────────────────────────────────────────────────────────┤
│   CLI (Typer)   │   API (FastAPI)   │   插件系统              │
└──────────────────────────────────────────────────────────────┘
```

## 支持的标准

- **TBX (ISO 30042)** -- 术语交换格式
- **TMX** -- 翻译记忆交换格式
- **BCP 47** -- 语言标签标识规范
- **Automotive SPICE 4.0** -- 过程合规证据（SWE.1-SWE.6、MAN.6）
- **UNECE R121** -- HMI 告警指示灯法规要求
- **Gherkin** -- 多语言 BDD 场景管理（支持 70+ 种语言）

## 开发

```bash
git clone https://github.com/BUNSEI1212/polydrive.git
cd polydrive

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
python -m pytest -v

# 代码检查
ruff check .
ruff format --check .
```

## 许可证

PolyDrive 采用 **Business Source License 1.1** (BSL 1.1) 发布。

- **非商业使用**：免费（学术研究、个人项目、开源项目）
- **商业使用**：需获取商业授权
- **转换日期**：每个版本发布 36 个月后自动转为 **Apache License 2.0**

详见 [LICENSE](LICENSE)。

## ML 增强功能（可选）

安装 `pip install polydrive[ml]` 可启用基于机器学习的增强模块，依赖包括 spaCy、sentence-transformers、KeyBERT：

- **Gherkin 跨语言语义匹配**：基于向量相似度检测不同语言版本的场景是否语义一致，弥补纯文本比对的不足
- **缺陷文本 NLP 质量分析**：自动评估缺陷描述的信息完整度、歧义性和可操作性
- **术语自动提取**：从技术文档和源码注释中自动抽取候选术语，辅助术语库建设

## 配置

PolyDrive 通过 YAML 配置文件管理项目级设置：

```bash
# 查看当前配置
polydrive config show

# 生成默认配置文件（polydrive.yaml）
polydrive config init
```

生成的配置文件涵盖语言对、术语表路径、翻译引擎偏好、编码规则、度量阈值等项目参数，可根据团队需求自定义。

## API 服务

通过 `polydrive serve` 启动内置 REST API 服务，所有 CLI 功能均可通过 HTTP 接口调用：

```bash
# 启动 API 服务（默认端口 8080）
polydrive serve --port 8080
```

服务启动后提供 16 个 REST 端点，覆盖术语管理、国际化检查、缺陷分析、翻译编排、追溯验证和度量导出等全部功能，便于与 CI/CD 管道或第三方工具集成。
