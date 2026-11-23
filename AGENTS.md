# gaokao-exam 项目约定

根级约定见 `../AGENTS.md`。本项目特有：

- **零 LLM 判分**：Part I–VII 全部走确定性判分（精确/归一化匹配、正则规则引擎、可执行单元测试、Lean 4 形式化校验）。不允许引入任何基于大模型的评分分支。
- **数据与 UI 解耦**：所有题目、答案、解析、知识点（`kp`）与语言学维度（`lexicon` / `morphosyntax` / `discourse` / `output`）一律存放在 `exams/*.json`，不得硬编码进 `src/web/ui.js` 或 `src/web/grader.js`。
- **同源判分引擎**：`src/web/grader.js` 同时供浏览器内联与 Node 自动化测试加载，保证网页判分与 pytest 的 golden-pass / negative-fail 行为一致。
- **Lean 4 防作弊不可绕过**：`src/graders/lean4.py` 与前端静态校验都必须先剥离注释，再拒绝 `sorry`、`admit`、`axiom`、`unsafe`、`implemented_by`、`extern` 并严格校验目标定理签名；调用 `lean` 编译器时还必须检查 `uses 'sorry'` 警告。
- **临时文件落在项目内**：CLI 判分与测试产生的临时文件一律写入 `artifacts/` 并及时清理，不依赖 `%TEMP%`。
- **产物不进版本库**：`artifacts/` 下生成的 `*.html` 可由 `python scripts/build_exam.py` 随时重生成，已列入 `.gitignore`。
- 提交信息风格见根级 `../AGENTS.md`。
