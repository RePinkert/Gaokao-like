(function () {
  const examData = window.__EXAM_DATA__;
  const grader = window.GaokaoGrader;
  let startedAt = Date.now();
  let timerHandle = null;
  let selectedLeftId = null;
  const part1Map = {};
  let externalPart7 = null;
  let lastReport = null;

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const key of Object.keys(attrs)) {
        if (key === "className") {
          node.className = attrs[key];
        } else if (key === "text") {
          node.textContent = attrs[key];
        } else if (key.startsWith("on") && typeof attrs[key] === "function") {
          node.addEventListener(key.slice(2).toLowerCase(), attrs[key]);
        } else {
          node.setAttribute(key, attrs[key]);
        }
      }
    }
    if (children) {
      for (const ch of children) {
        if (ch != null) {
          node.appendChild(typeof ch === "string" ? document.createTextNode(ch) : ch);
        }
      }
    }
    return node;
  }

  function formatTime(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
  }

  function startTimer() {
    const badge = document.getElementById("timer-badge");
    if (timerHandle) {
      clearInterval(timerHandle);
    }
    startedAt = Date.now();
    timerHandle = setInterval(function () {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      badge.textContent = formatTime(elapsed) + " / " + examData.meta.durationMinutes + "m";
    }, 1000);
  }

  function renderPassageWithBlanks(text, codeLike) {
    const box = el("div", { className: "passage-box" + (codeLike ? " code-like" : "") });
    const parts = String(text).split(/(\[\d+\])/g);
    for (const seg of parts) {
      if (/^\[\d+\]$/.test(seg)) {
        box.appendChild(el("span", { className: "inline-blank", text: seg }));
      } else {
        box.appendChild(document.createTextNode(seg));
      }
    }
    return box;
  }

  function renderPart1() {
    const sec = document.getElementById("sec-part1");
    const p1 = examData.parts.part1;
    const rightOptions = p1.pairs.map((p) => ({ rightId: p.rightId, text: p.right }));
    if (Array.isArray(p1.distractors)) {
      for (const d of p1.distractors) {
        rightOptions.push({ rightId: d.rightId, text: d.right });
      }
    }
    rightOptions.sort((a, b) => a.rightId.localeCompare(b.rightId));

    const leftCol = el("div", { id: "p1-left" });
    const rightCol = el("div", { id: "p1-right" });

    function refreshCards() {
      leftCol.innerHTML = "";
      rightCol.innerHTML = "";
      for (const pair of p1.pairs) {
        const assigned = part1Map[pair.id] || "";
        const card = el(
          "div",
          {
            className: "match-card" + (selectedLeftId === pair.id ? " selected" : ""),
            onClick: function () {
              selectedLeftId = selectedLeftId === pair.id ? null : pair.id;
              refreshCards();
            },
          },
          [
            el("div", { text: pair.id + ". " + pair.left }),
            el("span", {
              className: "match-badge" + (assigned ? " assigned" : ""),
              text: assigned || "?",
            }),
          ]
        );
        const fb = el("div", { className: "feedback", id: "fb-" + pair.id });
        leftCol.appendChild(card);
        leftCol.appendChild(fb);
      }

      const usedRights = new Set(Object.values(part1Map));
      for (const opt of rightOptions) {
        const card = el(
          "div",
          {
            className: "match-card",
            onClick: function () {
              if (!selectedLeftId) {
                return;
              }
              part1Map[selectedLeftId] = opt.rightId;
              selectedLeftId = null;
              refreshCards();
            },
          },
          [
            el("span", {
              className: "match-badge" + (usedRights.has(opt.rightId) ? " assigned" : ""),
              text: opt.rightId,
            }),
            el("div", { text: opt.text }),
          ]
        );
        rightCol.appendChild(card);
      }
    }

    sec.appendChild(
      el("div", { className: "section-header" }, [
        el("h2", { text: "Part I: Concept Matching" }),
        el("span", { className: "section-subtitle", text: "Click a concept on the left, then click its match on the right." }),
      ])
    );
    sec.appendChild(el("div", { className: "matching-grid" }, [leftCol, rightCol]));
    refreshCards();
    window.__refreshPart1 = refreshCards;
  }

  function renderPart2() {
    const sec = document.getElementById("sec-part2");
    const isCode = examData.meta.domain === "programming" || examData.meta.domain === "mathematics";
    sec.appendChild(
      el("div", { className: "section-header" }, [
        el("h2", { text: "Part II: Reading Comprehension" }),
        el("span", { className: "section-subtitle", text: "Comprehensible input and inference" }),
      ])
    );
    for (const psg of examData.parts.part2.passages) {
      const qCol = el("div");
      for (const q of psg.items) {
        const optsWrap = el("div", { className: "options-list" });
        for (const key of Object.keys(q.options)) {
          const inp = el("input", { type: "radio", name: "p2-" + q.id, value: key });
          optsWrap.appendChild(el("label", { className: "option-label" }, [inp, el("span", { text: key + ". " + q.options[key] })]));
        }
        qCol.appendChild(
          el("div", { className: "question-block" }, [
            el("div", { className: "question-stem", text: q.id + ". " + q.stem }),
            optsWrap,
            el("div", { className: "feedback", id: "fb-" + q.id }),
          ])
        );
      }
      const pBox = el("div", {}, [
        el("h3", { text: psg.title }),
        el("div", { className: "passage-box" + (isCode ? " code-like" : ""), text: psg.body }),
      ]);
      sec.appendChild(el("div", { className: "split-layout" }, [pBox, qCol]));
    }
  }

  function renderPart3() {
    const sec = document.getElementById("sec-part3");
    const p3 = examData.parts.part3;
    const isCode = examData.meta.domain === "programming" || examData.meta.domain === "mathematics";
    sec.appendChild(
      el("div", { className: "section-header" }, [
        el("h2", { text: "Part III: 7-Choose-5 (Cohesion)" }),
        el("span", { className: "section-subtitle", text: "Select 5 of 7 options to restore logical flow (2 distractors)" }),
      ])
    );
    const left = renderPassageWithBlanks(p3.passage, isCode);
    const right = el("div");
    const bank = el("div", { className: "question-block" }, [el("div", { className: "question-stem", text: "Option Bank (A-G)" })]);
    for (const opt of p3.options) {
      bank.appendChild(el("div", { text: opt.id + ". " + opt.text }));
    }
    right.appendChild(bank);

    for (const item of p3.items) {
      const sel = el("select", { id: "p3-" + item.id });
      sel.appendChild(el("option", { value: "", text: "-- choose --" }));
      for (const opt of p3.options) {
        sel.appendChild(el("option", { value: opt.id, text: opt.id }));
      }
      right.appendChild(
        el("div", { className: "question-block" }, [
          el("div", { className: "question-stem", text: "Blank " + item.id }),
          sel,
          el("div", { className: "feedback", id: "fb-" + item.id }),
        ])
      );
    }
    sec.appendChild(el("div", { className: "split-layout" }, [left, right]));
  }

  function renderPart4() {
    const sec = document.getElementById("sec-part4");
    const p4 = examData.parts.part4;
    const isCode = examData.meta.domain === "programming" || examData.meta.domain === "mathematics";
    sec.appendChild(
      el("div", { className: "section-header" }, [
        el("h2", { text: "Part IV: Cloze Test" }),
        el("span", { className: "section-subtitle", text: "Contextual lexical-semantic selection" }),
      ])
    );
    sec.appendChild(renderPassageWithBlanks(p4.passage, isCode));
    const grid = el("div", { className: "cloze-grid" });
    for (const item of p4.items) {
      const sel = el("select", { id: "p4-" + item.id });
      sel.appendChild(el("option", { value: "", text: "-- select --" }));
      for (const key of Object.keys(item.options)) {
        sel.appendChild(el("option", { value: key, text: key + ". " + item.options[key] }));
      }
      grid.appendChild(
        el("div", { className: "question-block" }, [
          el("div", { className: "question-stem", text: "Blank " + item.id }),
          sel,
          el("div", { className: "feedback", id: "fb-" + item.id }),
        ])
      );
    }
    sec.appendChild(grid);
  }

  function renderPart5() {
    const sec = document.getElementById("sec-part5");
    const p5 = examData.parts.part5;
    const isCode = examData.meta.domain === "programming" || examData.meta.domain === "mathematics";
    sec.appendChild(
      el("div", { className: "section-header" }, [
        el("h2", { text: "Part V: Grammar Fill-in" }),
        el("span", { className: "section-subtitle", text: "Morphosyntactic and symbolic transformation" }),
      ])
    );
    sec.appendChild(renderPassageWithBlanks(p5.passage, isCode));
    const grid = el("div", { className: "cloze-grid" });
    for (const item of p5.items) {
      const label = item.prompt ? item.id + " (prompt: " + item.prompt + ")" : item.id;
      const inp = el("input", { type: "text", className: "fill-input", id: "p5-" + item.id, placeholder: "Type answer" });
      grid.appendChild(
        el("div", { className: "question-block" }, [
          el("div", { className: "question-stem", text: label }),
          inp,
          el("div", { className: "feedback", id: "fb-" + item.id }),
        ])
      );
    }
    sec.appendChild(grid);
  }

  function renderPart6() {
    const sec = document.getElementById("sec-part6");
    const p6 = examData.parts.part6;
    const isCode = examData.meta.domain === "programming" || examData.meta.domain === "mathematics";
    sec.appendChild(
      el("div", { className: "section-header" }, [
        el("h2", { text: "Part VI: Error Correction" }),
        el("span", { className: "section-subtitle", text: "Specify operation (add / delete / replace) and canonical fix" }),
      ])
    );
    const linesBox = el("div", { className: "passage-box" + (isCode ? " code-like" : "") });
    for (const ln of p6.lines) {
      linesBox.appendChild(
        el("div", { className: "error-line" }, [
          el("span", { className: "line-no", text: "L" + ln.line }),
          el("span", { text: ln.text }),
        ])
      );
    }
    const qCol = el("div");
    for (const item of p6.items) {
      const opSel = el("select", { id: "p6-op-" + item.id });
      for (const op of ["", "add", "delete", "replace"]) {
        opSel.appendChild(el("option", { value: op, text: op || "-- op --" }));
      }
      const fixInp = el("input", {
        type: "text",
        className: "fix-input",
        id: "p6-fix-" + item.id,
        placeholder: "Fix token (leave blank for delete)",
      });
      qCol.appendChild(
        el("div", { className: "question-block" }, [
          el("div", { className: "question-stem", text: item.id + " (Line " + item.line + ", target: " + item.target + ")" }),
          el("div", { className: "part7-tools" }, [opSel, fixInp]),
          el("div", { className: "feedback", id: "fb-" + item.id }),
        ])
      );
    }
    sec.appendChild(el("div", { className: "split-layout" }, [linesBox, qCol]));
  }

  function renderPart7() {
    const sec = document.getElementById("sec-part7");
    const p7 = examData.parts.part7;
    sec.appendChild(
      el("div", { className: "section-header" }, [
        el("h2", { text: "Part VII: Controlled Output & Formal Verification" }),
        el("span", { className: "section-subtitle", text: "Deterministic mode: " + p7.mode }),
      ])
    );
    sec.appendChild(el("div", { className: "passage-box", text: p7.prompt }));
    const editor = el("textarea", { className: "code-editor", id: "p7-editor" });
    editor.value = p7.starterCode;
    sec.appendChild(editor);

    const toolsRow = el("div", { className: "part7-tools" });
    if (p7.mode === "js-unit") {
      toolsRow.appendChild(
        el("button", {
          type: "button",
          text: "Run Unit Tests Now",
          onClick: function () {
            const res = grader.gradeJsUnit(p7, editor.value);
            renderPart7Live(res);
          },
        })
      );
    } else if (p7.mode === "nl-rules") {
      const counter = el("span", { className: "exam-meta", id: "p7-word-count", text: "Words: 0" });
      editor.addEventListener("input", function () {
        const n = editor.value.trim() ? editor.value.trim().split(/\s+/).length : 0;
        counter.textContent = "Words: " + n + " (target " + p7.minWords + "-" + p7.maxWords + ")";
      });
      toolsRow.appendChild(
        el("button", {
          type: "button",
          text: "Check Rules Now",
          onClick: function () {
            const res = grader.gradeNlRules(p7, editor.value);
            renderPart7Live(res);
          },
        })
      );
      toolsRow.appendChild(counter);
    } else if (p7.mode === "lean4") {
      toolsRow.appendChild(
        el("button", {
          type: "button",
          text: "Download Part7.lean",
          onClick: function () {
            downloadFile("Part7.lean", editor.value, "text/plain");
          },
        })
      );
      toolsRow.appendChild(
        el("button", {
          type: "button",
          text: "Copy CLI Grader Command",
          onClick: function () {
            const cmd = "python scripts/grade_part7.py exams/" + examData.meta.id + ".json Part7.lean";
            if (navigator.clipboard) {
              navigator.clipboard.writeText(cmd);
            }
            alert("CLI command: " + cmd);
          },
        })
      );
      if (Array.isArray(p7.quickChecks) && p7.quickChecks.length > 0) {
        const qcWrap = el("div", { className: "cloze-grid" });
        for (const qc of p7.quickChecks) {
          qcWrap.appendChild(
            el("div", { className: "question-block" }, [
              el("div", { className: "question-stem", text: "Quick Check " + qc.id + ": " + qc.question }),
              el("input", { type: "text", className: "fill-input", id: "p7-qc-" + qc.id, placeholder: "Answer" }),
            ])
          );
        }
        sec.appendChild(qcWrap);
      }
      const importBox = el("textarea", {
        className: "code-editor",
        id: "p7-import-json",
        placeholder: "Paste JSON output from scripts/grade_part7.py here, then click Import CLI Result",
      });
      importBox.style.minHeight = "72px";
      const importBtn = el("button", {
        type: "button",
        text: "Import CLI Result JSON",
        onClick: function () {
          try {
            externalPart7 = JSON.parse(importBox.value);
            alert("Imported CLI verification result: passed=" + Boolean(externalPart7.passed));
          } catch (err) {
            alert("Invalid JSON: " + err.message);
          }
        },
      });
      sec.appendChild(importBox);
      toolsRow.appendChild(importBtn);
    }

    sec.appendChild(toolsRow);
    sec.appendChild(el("div", { className: "feedback", id: "fb-" + p7.id }));
    sec.appendChild(el("div", { id: "p7-live-detail" }));
  }

  function renderPart7Live(res) {
    const box = document.getElementById("p7-live-detail");
    box.innerHTML = "";
    const list = res.cases || res.checks || [];
    const ul = el("ul");
    for (const item of list) {
      const label = (item.passed ? "[PASS] " : "[FAIL] ") + item.name + (item.detail ? " - " + item.detail : "");
      ul.appendChild(el("li", { text: label }));
    }
    box.appendChild(ul);
  }

  function collectAnswers() {
    const answers = {
      part1: Object.assign({}, part1Map),
      part2: {},
      part3: {},
      part4: {},
      part5: {},
      part6: {},
      part7: "",
    };
    for (const psg of examData.parts.part2.passages) {
      for (const q of psg.items) {
        const checked = document.querySelector('input[name="p2-' + q.id + '"]:checked');
        answers.part2[q.id] = checked ? checked.value : "";
      }
    }
    for (const q of examData.parts.part3.items) {
      answers.part3[q.id] = document.getElementById("p3-" + q.id).value;
    }
    for (const q of examData.parts.part4.items) {
      answers.part4[q.id] = document.getElementById("p4-" + q.id).value;
    }
    for (const q of examData.parts.part5.items) {
      answers.part5[q.id] = document.getElementById("p5-" + q.id).value;
    }
    for (const q of examData.parts.part6.items) {
      answers.part6[q.id] = {
        op: document.getElementById("p6-op-" + q.id).value,
        fix: document.getElementById("p6-fix-" + q.id).value,
      };
    }
    const editorVal = document.getElementById("p7-editor").value;
    if (examData.parts.part7.mode === "lean4") {
      const qcAns = {};
      for (const qc of examData.parts.part7.quickChecks || []) {
        const node = document.getElementById("p7-qc-" + qc.id);
        qcAns[qc.id] = node ? node.value : "";
      }
      answers.part7 = { code: editorVal, quickChecks: qcAns };
    } else {
      answers.part7 = editorVal;
    }
    return answers;
  }

  function renderReport(report) {
    lastReport = report;
    for (const it of report.items) {
      const fb = document.getElementById("fb-" + it.id);
      if (!fb) {
        continue;
      }
      fb.className = "feedback show " + (it.correct ? "ok" : "bad");
      const status = it.correct ? "Correct (" + it.earned + "/" + it.maxPoints + ")" : "Incorrect (" + it.earned + "/" + it.maxPoints + ") - Key: " + it.expected;
      fb.textContent = status + " | " + it.explanation + (it.detail ? " [" + it.detail + "]" : "");
    }
    renderPart7Live(report.part7Detail);

    const panel = document.getElementById("report-panel");
    panel.innerHTML = "";
    panel.className = "report-panel show";
    panel.appendChild(el("h2", { text: "Linguistic Diagnostic Report" }));

    panel.appendChild(
      el("div", { className: "summary-grid" }, [
        el("div", { className: "stat-card" }, [
          el("div", { className: "stat-value", text: report.summary.earned + " / " + report.summary.maxPoints }),
          el("div", { className: "stat-label", text: "Total Score" }),
        ]),
        el("div", { className: "stat-card" }, [
          el("div", { className: "stat-value", text: report.summary.accuracy + "%" }),
          el("div", { className: "stat-label", text: "Overall Accuracy" }),
        ]),
        el("div", { className: "stat-card" }, [
          el("div", { className: "stat-value", text: formatTime(report.meta.elapsedSeconds) }),
          el("div", { className: "stat-label", text: "Elapsed Time" }),
        ]),
        el("div", { className: "stat-card" }, [
          el("div", { className: "stat-value", text: report.meta.domain }),
          el("div", { className: "stat-label", text: "Domain" }),
        ]),
      ])
    );

    panel.appendChild(el("h3", { text: "4-Dimension Linguistic Breakdown" }));
    for (const dim of grader.DIMENSIONS) {
      const d = report.dimensions[dim];
      const fill = el("div", { className: "bar-fill" });
      fill.style.width = d.accuracy + "%";
      panel.appendChild(
        el("div", { className: "dim-bar-row" }, [
          el("strong", { text: dim }),
          el("div", { className: "bar-track" }, [fill]),
          el("span", { text: d.accuracy + "%" }),
        ])
      );
    }

    if (report.patterns.length > 0) {
      const pBox = el("div", { className: "pattern-box" });
      for (const pat of report.patterns) {
        pBox.appendChild(el("div", { text: "- " + pat }));
      }
      panel.appendChild(pBox);
    }

    panel.appendChild(el("h3", { text: "Section Breakdown" }));
    const secTable = el("table", { className: "report-table" });
    secTable.appendChild(
      el("tr", {}, [
        el("th", { text: "Section" }),
        el("th", { text: "Score" }),
        el("th", { text: "Items Correct" }),
        el("th", { text: "Accuracy" }),
      ])
    );
    for (const s of report.sections) {
      secTable.appendChild(
        el("tr", {}, [
          el("td", { text: s.part.toUpperCase() }),
          el("td", { text: s.earned + " / " + s.maxPoints }),
          el("td", { text: s.correctCount + " / " + s.totalCount }),
          el("td", { text: s.accuracy + "%" }),
        ])
      );
    }
    panel.appendChild(secTable);

    panel.appendChild(el("h3", { text: "i+1 Weakness Map" }));
    if (report.weaknessMap.length === 0) {
      panel.appendChild(el("p", { text: "No missed knowledge points." }));
    } else {
      const wTable = el("table", { className: "report-table" });
      wTable.appendChild(
        el("tr", {}, [
          el("th", { text: "Knowledge Point" }),
          el("th", { text: "Dimension" }),
          el("th", { text: "Accuracy" }),
          el("th", { text: "Missed Items" }),
          el("th", { text: "Remediation" }),
        ])
      );
      for (const w of report.weaknessMap) {
        wTable.appendChild(
          el("tr", {}, [
            el("td", { text: w.name }),
            el("td", { text: w.dimension }),
            el("td", { text: w.accuracy + "%" }),
            el("td", { text: w.missedItems.join(", ") }),
            el("td", { text: w.remediation }),
          ])
        );
      }
      panel.appendChild(wTable);
    }

    panel.scrollIntoView({ behavior: "smooth" });
  }

  function downloadFile(filename, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function init() {
    document.title = examData.meta.title;
    document.getElementById("exam-title").textContent = examData.meta.title;
    document.getElementById("exam-meta").textContent =
      "Domain: " + examData.meta.domain + " | Scale: " + examData.meta.scale + " | Time: " + examData.meta.durationMinutes + " min";

    renderPart1();
    renderPart2();
    renderPart3();
    renderPart4();
    renderPart5();
    renderPart6();
    renderPart7();
    startTimer();

    document.getElementById("btn-submit").addEventListener("click", function () {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      const answers = collectAnswers();
      const report = grader.gradeExam(examData, answers, {
        elapsedSeconds: elapsed,
        externalPart7: externalPart7,
      });
      renderReport(report);
    });

    document.getElementById("btn-export").addEventListener("click", function () {
      if (!lastReport) {
        alert("Submit the exam first to generate a diagnostic report.");
        return;
      }
      downloadFile(examData.meta.id + "-report.json", JSON.stringify(lastReport, null, 2), "application/json");
    });

    document.getElementById("btn-reset").addEventListener("click", function () {
      window.location.reload();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
