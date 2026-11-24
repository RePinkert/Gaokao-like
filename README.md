# Gaokao-like

将任意学习材料（自然语言、编程语言、数学/形式系统）按高考英语七大题型（听力替换为概念匹配/连线）构建为独立可运行的交互式网页试卷，配备零 LLM 的确定性自动判分（JS 单元测试、带防 `sorry`/签名校验的 Lean 4 验证器、自然语言规则引擎）与四维语言学诊断报告。

## 跑起来

构建全部示例试卷到 `artifacts/*.html`（浏览器直接打开即可答题与判分）：

```powershell
cd Gaokao-like
python scripts/build_exam.py
```

构建单份试卷：

```powershell
python scripts/build_exam.py exams/math-logic-lean4.json artifacts/math-logic-lean4.html
```

对 Part VII 外部提交跑确定性 CLI 判分（输出 JSON 可直接导入网页更新总分与四维诊断）：

```powershell
python scripts/grade_part7.py exams/math-logic-lean4.json Part7.lean
python scripts/grade_part7.py exams/math-logic-lean4.json Part7.lean --static-only
```

## 测一遍

```powershell
cd Gaokao-like
python scripts/check.py
python -m pytest -q tests
```

静态检查强制零注释且仅允许 `README.md` 与 `AGENTS.md`；测试覆盖题库 schema 校验、三类领域试卷的 golden-pass（100%）与 negative-fail、Part VII 的 Lean 4 防作弊与 CLI 判分，以及独立 HTML 构建验证。

## 目录

```
Gaokao-like/
  README.md       项目说明、运行与测试入口
  AGENTS.md       本项目特有约定
  exams/          数据驱动题库 JSON（数学/Lean 4、编程/JS、自然语言）
  src/
    schema.py     七大题型与四维标签 schema 校验器
    builder.py    独立 HTML 试卷生成器
    graders/      Part VII 确定性判分器（Lean 4 防作弊、Node/规则引擎桥接）
    web/          浏览器与 Node 共用的判分引擎、交互 UI、样式与模板
  scripts/        check.py、build_exam.py、grade_part7.py
  tests/          schema、判分、防作弊与构建测试
  hooks/          pre-commit：提交前强制跑 check.py 与 pytest
  artifacts/      生成的独立 HTML 试卷（不进版本库）
```
