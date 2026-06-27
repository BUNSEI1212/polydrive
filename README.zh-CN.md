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

# 检查文件编码（检测非 UTF-8 与 BOM 问题）
polydrive i18n check-encoding examples/bad_encoding/ --require-utf8 --fail-on-bom

# 检测 C/C++ 源码中的硬编码 CJK 字符
polydrive i18n detect-hardcoded examples/cpp_project/ --lang cpp

# 导入多语种术语表
polydrive glossary import examples/automotive_terms.csv

# 生成伪本地化资源
polydrive i18n pseudo-localize examples/locales/en.json --mode expand+cjk

# 分析缺陷报告质量
polydrive defect analyze --input examples/bug_report_zh.json

# 启动 REST API 服务
polydrive serve --port 8080
```

详见 [examples/README.md](examples/README.md) 获取完整 Demo 说明。

## 演示

以下命令均基于内置的 `examples/` 数据运行。输出已为可读性精简——自行运行可查看完整的 Rich 渲染表格。

**编码守卫** — 在非 UTF-8 文件与 BOM 标记破坏多语言 CI 管道之前将其标出：

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

**硬编码字符串检测** — 找出嵌在 C/C++ 源码中、本应放入 i18n 资源的 CJK 字面量：

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

**缺陷报告质量** — 对一份跨语言缺陷报告评分，并暴露其中缺失的内容：

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

**伪本地化** — 在真实翻译落地之前，先压测 HMI 布局。`"Engine Temperature"` → `"[Êñ夕ïñê 七ê山巳ê尺ä七û尺ê -------]"`（expand+cjk 模式），写入 `examples/locales/en.pseudo.json`。

## 更多命令

```bash
# 术语一致性检查（需要 TBX 格式）
polydrive glossary check terms.tbx --lang-pair en:zh

# 带术语约束的翻译（德语 -> 英语）
polydrive mt translate --text "Bremsfehler erkannt" --from de --to en --glossary terms.tbx

# 验证 Qt 翻译文件
polydrive i18n validate-qt translations/app_zh_CN.ts

# 检查 Gherkin 跨语言场景同步
polydrive trace sync-gherkin --base en --compare zh,de --features tests/

# 检查 UNECE R121 HMI 合规性
polydrive trace unece-check --manifest hmi_manifest.json

# 收集 ASPICE 语言合规证据
polydrive trace aspice-evidence --project .

# 查看质量度量摘要
polydrive metrics summary --input metrics.json
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

## CI 集成

PolyDrive 提供一个可复用的 GitHub Action，将 i18n 检查作为 PR 门禁运行：

```yaml
- uses: BUNSEI1212/polydrive/.github/actions/i18n-check@v0.1.0
  with:
    path: src
    # install-command 默认为 `pip install polydrive`；
    # 对源码检出可使用例如 `pip install -e .`
```

它会运行 `check-encoding`（带 `--require-utf8 --fail-on-bom`），并在存在 C/C++ 源码时运行 `detect-hardcoded`。两者在检出问题时均以非零状态退出，因此一次检查即可阻断合并。本仓库在 `.github/workflows/i18n-guard.yml` 中 dogfood 该 Action。

## 影响与路线图

### 谁在承受这份痛点

PolyDrive 针对的是跨国汽车**测试团队**每天都会碰到的摩擦——而不是孤立的翻译团队：

- **分布式测试台架**（德国/中国/日本/美国）以母语提交缺陷；接收方团队必须复现一份在翻译中语义已发生漂移的 bug 描述。PolyDrive 的 `defect` 模块对可复现性评分，并标记语言混用，让缺口在分流前就可见。
- **HMI 认证**必须满足区域性的告警指示灯/标识法规。`trace` 一次性检查 UNECE R121 合规性并收集 ASPICE 语言证据，而无需手动维护审计表格。
- **CI 管道**会在 Shift-JIS 或 GB2312 源文件落入 UTF-8 工具链时静默崩溃。`i18n check-encoding` 把它变成一次快速而响亮的失败。
- **术语漂移**在 需求 → 测试 → 缺陷 之间传递会侵蚀追溯性。`glossary` 在跨语言间维护一份权威术语集。

PolyDrive 刻意保持专注且开放：它把术语、缺陷质量、i18n 守卫和追溯性连接到一个适配 CI 步骤的 CLI 里——这正是大多数现有工具留给电子表格和临时脚本的空白。

### 路线图

PolyDrive 尚处早期（0.x）。以下为计划方向，启动后会作为 GitHub issue 跟踪：

- **更多标准**：ISO 26262 安全术语、ISO/SAE 21434 网络安全术语、AUTOSAR ARXML 抽取、ISO 9241 HMI 人因工程检查。
- **翻译质量**：在 `mt` 网关上做 MQM/DAQP 错误类型学评分，而不只是透传翻译。
- **自动化**：从既有缺陷/测试语料中抽取术语以引导建立术语库，并提供一等公民的 GitHub Action，让每项检查都在 PR 上运行。
- **生态**：语言服务器 / IDE 集成，让术语与硬编码字符串告警在编写时而非提交后才暴露。
- **覆盖面**：更多 BCP 47 区域设置，以及在现有 REST API 之上构建 Web UI。

BSL → Apache 2.0 转换（每个版本 36 个月）让长尾保持完全开放，同时以早期商业使用资助维护。

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

## 维护与治理

PolyDrive 目前由**单人维护者**维护。为了在这种规模下保持可持续，工作流刻意以工具辅助、流程轻量为导向：

- **Issue 分流** — bug 与功能请求进入
  [GitHub Issues](https://github.com/BUNSEI1212/polydrive/issues)，并按模块（`glossary`、`i18n`、`defect`……）和类型（`bug`、`enhancement`、`standard`）打标签。一份清晰的复现说明（输入文件 + 命令 + 预期 vs 实际）会让 issue 排到队列最前。
- **功能规划** — 较大的工作会对照[路线图](#影响与路线图)界定范围，并在代码落地前通过里程碑跟踪，从而保持范围有界。请先通过打了 `discussion` 标签的 issue 提出想法。
- **工具杠杆** — 维护者借助自动化放大产出：CI 矩阵捕获平台回归，`ruff` + `pytest` 在每次变更时守护风格与行为，PolyDrive 自身也经过[dogfooded](https://en.wikipedia.org/wiki/Eating_your_own_dog_food)——它自己的 CLI 检查会针对内置示例作为集成测试运行（`tests/test_examples.py`），并作为可复用的 GitHub Action 在每个 PR 上把关（`.github/workflows/i18n-guard.yml`）。AI 辅助开发处理常规重构与测试脚手架，让评审聚焦于设计。
- **发布** — 按 semver 进行版本管理；BSL 转换日期机制在每个版本发布 36 个月后将其转为 Apache 2.0，即使项目演进，旧版本仍可使用。

欢迎贡献——参见 [CONTRIBUTING.md](CONTRIBUTING.md)。如需商业使用或自定义转换日期，请开一个 issue 讨论授权事宜。

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
