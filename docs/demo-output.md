# Demo Output

Real output from running PolyDrive commands against the example data in `examples/`.

---

## 1. Version & Help

```
$ polydrive --version
polydrive 0.1.0

$ polydrive --help

 Usage: polydrive [OPTIONS] COMMAND [ARGS]...

 Language governance toolkit for multinational automotive testing.

 Commands:
   serve      Start the PolyDrive REST API server.
   glossary   Terminology engine: import, check, and manage multilingual glossaries.
   i18n       Internationalization guard: encoding checks, hardcoded string detection, pseudo-localization.
   defect     Defect report quality analysis and template validation.
   metrics    Quality metrics: summary, Prometheus export, and HTML reports.
   mt         Machine translation gateway: translate text via multiple MT engines.
   trace      Cross-language traceability: Gherkin sync, UNECE compliance, ASPICE evidence.
   config     Configuration management: show or initialize PolyDrive settings.
```

---

## 2. Detect Hardcoded CJK Strings in C/C++

```
$ polydrive i18n detect-hardcoded examples/cpp_project/ --lang cpp

 Hardcoded Strings in examples/cpp_project/
┌─────────────────────────────────┬──────┬─────┬──────────────────────────────────┐
│ File                            │ Line │ Col │ Text                             │
├─────────────────────────────────┼──────┼─────┼──────────────────────────────────┤
│ dashboard.cpp                   │    8 │   7 │ 制动液位过低，请及时补充          │
│ dashboard.cpp                   │   10 │  30 │ 制动系统故障，请立即停车检查      │
│ dashboard.cpp                   │   14 │  31 │ 制动器温度过高，请注意冷却        │
│ dashboard.cpp                   │   23 │   5 │ 电量严重不足，请立即充电          │
│ dashboard.cpp                   │   25 │  11 │ 电量较低，建议尽快充电            │
│ instrument_cluster.cpp          │    6 │   7 │ 点検時期が過ぎています            │
│ instrument_cluster.cpp          │    8 │  14 │ まもなく点検時期です              │
│ instrument_cluster.cpp          │   15 │   9 │ ドアが開いています                │
│ instrument_cluster.cpp          │   18 │   9 │ ドアが完全に閉じていません        │
└─────────────────────────────────┴──────┴─────┴──────────────────────────────────┘

Found 9 hardcoded non-ASCII string(s)
```

---

## 3. Import Multilingual Glossary

```
$ polydrive glossary import examples/automotive_terms.csv

Imported 11 entries from automotive_terms.csv (domain: automotive)

                               Glossary Summary
┌──────────────────────┬──────────────────────┬──────────────────┬────────────┐
│ ID                   │ Source Term          │ Target Term      │ Category   │
├──────────────────────┼──────────────────────┼──────────────────┼────────────┤
│ brake_energy_recove… │ brake energy         │ 制动能量回收     │ technical  │
│                      │ recovery             │                  │            │
│ adas                 │ ADAS                 │ 高级驾驶辅助系统 │ technical  │
│ ecu                  │ ECU                  │ 电子控制单元     │ technical  │
│ can_bus              │ CAN bus              │ CAN总线          │ technical  │
│ torque_vectoring     │ torque vectoring     │ 扭矩矢量分配     │ technical  │
│ tell_tale            │ tell-tale            │ 指示灯           │ regulatory │
│ hmi                  │ HMI                  │ 人机界面         │ technical  │
│ soc                  │ SOC                  │ 荷电状态         │ technical  │
│ ota                  │ OTA                  │ 空中升级         │ technical  │
│ fault_code           │ fault code           │ 故障码           │ technical  │
│ repro_steps          │ reproduction steps   │ 复现步骤         │ technical  │
└──────────────────────┴──────────────────────┴──────────────────┴────────────┘
```

Each entry has translations in en, zh, de, ja. For example, `brake_energy_recovery`:
- en: brake energy recovery
- zh: 制动能量回收
- de: Bremsenergierückgewinnung
- ja: ブレーキエネルギー回生

---

## 4. Analyze a Defect Report

```
$ polydrive defect analyze --input examples/bug_report_zh.json

Defect Report Quality Analysis
  Report ID:        BUG-2024-0158
  Composite Score:   76.6/100
  Completeness:      87.5/100
  Text Quality:      51.4/100
  Reproducibility:   75.0/100
  Terminology:       100.0/100
  Language:          no
  Language Mix:      Language mixing detected: 48% non-dominant script (dominant: cjk)
  Missing Fields:    ['environment']
  Severity:          info

  Improvement Suggestions:
    - Add environment details (OS, version, platform, etc.)
    - Description is a single sentence — add more detail
    - No technical terms or acronyms detected
    - No version numbers mentioned
```

Key findings from the analysis:
- **Score 76.6** — The report is above average but has clear improvement areas
- **Missing `environment` field** — Critical for reproducing issues across teams
- **Language mixing** — Chinese, English, and German text detected (48% non-dominant)
- **Terminology 100%** — All terms match the automotive glossary

---

## 5. Generate Pseudo-Localized Resources

```
$ polydrive i18n pseudo-localize examples/locales/en.json --mode expand+cjk
```

Output written to `examples/locales/en.pseudo.json`:

```json
{
  "dashboard": {
    "speed": "[双巳êê己 --]",
    "fuel_level": "[叭ûê叩 叩ê丟ê叩 ----]",
    "engine_temp": "[Êñ夕ïñê 七ê山巳ê尺ä七û尺ê -------]"
  },
  "warnings": {
    "low_fuel": "[叩õ穴 叭ûê叩 ---]",
    "overheat": "[Êñ夕ïñê Õ丟ê尺千êä七ïñ夕 -------]",
    "tire_pressure": "[七ï尺ê 巳尺ê双双û尺ê 叩õ穴 ------]"
  },
  "navigation": {
    "destination": "[Êñ七ê尺 丁ê双七ïñä七ïõñ ------]",
    "turn_left": "[七û尺ñ 叩ê干七 ---]",
    "turn_right": "[七û尺ñ 尺ï夕千七 ----]"
  }
}
```

The CJK + expand mode transforms ASCII strings into pseudo-CJK characters with text expansion, useful for detecting HMI layout overflow issues before actual translation.

---

## 6. Start REST API Server

```
$ polydrive serve --help

 Usage: polydrive serve [OPTIONS]

 Start the PolyDrive REST API server.

 Options:
   --host      TEXT      Bind host [default: 0.0.0.0]
   --port      INTEGER   Bind port [default: 8080]
   --reload              Enable auto-reload
   --help                Show this message and exit

$ polydrive serve --port 8080
Starting PolyDrive API at http://0.0.0.0:8080
  Docs: http://0.0.0.0:8080/docs
```

Once running, visit `http://localhost:8080/docs` for the interactive Swagger UI with 16 REST endpoints.
