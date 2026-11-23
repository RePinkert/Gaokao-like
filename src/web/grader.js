(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.GaokaoGrader = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const DIMENSIONS = ["lexicon", "morphosyntax", "discourse", "output"];

  function normalizeText(value, caseSensitive) {
    const raw = String(value == null ? "" : value).trim().replace(/\s+/g, " ");
    return caseSensitive ? raw : raw.toLowerCase();
  }

  function stripLeanComments(code) {
    let out = "";
    let i = 0;
    const n = code.length;
    while (i < n) {
      if (code[i] === "/" && code[i + 1] === "-") {
        let depth = 1;
        i += 2;
        while (i < n && depth > 0) {
          if (code[i] === "/" && code[i + 1] === "-") {
            depth += 1;
            i += 2;
          } else if (code[i] === "-" && code[i + 1] === "/") {
            depth -= 1;
            i += 2;
          } else {
            i += 1;
          }
        }
        out += " ";
        continue;
      }
      if (code[i] === "-" && code[i + 1] === "-") {
        while (i < n && code[i] !== "\n") {
          i += 1;
        }
        continue;
      }
      out += code[i];
      i += 1;
    }
    return out;
  }

  function deepEqual(a, b) {
    if (Object.is(a, b)) {
      return true;
    }
    if (typeof a !== typeof b || a === null || b === null) {
      return false;
    }
    if (Array.isArray(a) && Array.isArray(b)) {
      if (a.length !== b.length) {
        return false;
      }
      for (let i = 0; i < a.length; i += 1) {
        if (!deepEqual(a[i], b[i])) {
          return false;
        }
      }
      return true;
    }
    if (typeof a === "object" && !Array.isArray(a) && !Array.isArray(b)) {
      const ka = Object.keys(a).sort();
      const kb = Object.keys(b).sort();
      if (!deepEqual(ka, kb)) {
        return false;
      }
      for (const k of ka) {
        if (!deepEqual(a[k], b[k])) {
          return false;
        }
      }
      return true;
    }
    return false;
  }

  function gradeJsUnit(part7, code) {
    const src = String(code || "");
    const results = [];
    if (!src.trim()) {
      return {
        passed: false,
        earned: 0,
        maxPoints: part7.points,
        details: ["Submission is empty."],
        cases: [],
      };
    }
    let fn;
    try {
      const factory = new Function(src + "\nreturn typeof " + part7.functionName + " === 'function' ? " + part7.functionName + " : null;");
      fn = factory();
    } catch (err) {
      return {
        passed: false,
        earned: 0,
        maxPoints: part7.points,
        details: ["Syntax or runtime error while loading code: " + err.message],
        cases: [],
      };
    }
    if (typeof fn !== "function") {
      return {
        passed: false,
        earned: 0,
        maxPoints: part7.points,
        details: ["Expected function named " + part7.functionName + "."],
        cases: [],
      };
    }
    let passedCount = 0;
    for (const tc of part7.cases) {
      try {
        let actual;
        if (typeof tc.expression === "string") {
          const runner = new Function(part7.functionName, "return (" + tc.expression + ");");
          actual = runner(fn);
        } else {
          actual = fn.apply(null, tc.args || []);
        }
        const ok = deepEqual(actual, tc.expected);
        if (ok) {
          passedCount += 1;
        }
        results.push({
          name: tc.name,
          passed: ok,
          expected: tc.expected,
          actual: actual,
        });
      } catch (err) {
        results.push({
          name: tc.name,
          passed: false,
          expected: tc.expected,
          error: err.message,
        });
      }
    }
    const allPassed = passedCount === part7.cases.length;
    const earned = Math.round((part7.points * passedCount) / part7.cases.length * 100) / 100;
    return {
      passed: allPassed,
      earned: earned,
      maxPoints: part7.points,
      details: [passedCount + " / " + part7.cases.length + " unit tests passed."],
      cases: results,
    };
  }

  function gradeNlRules(part7, text) {
    const raw = String(text || "").trim();
    if (!raw) {
      return {
        passed: false,
        earned: 0,
        maxPoints: part7.points,
        details: ["Submission is empty."],
        checks: [],
      };
    }
    const words = raw.split(/\s+/).filter(Boolean);
    const checks = [];
    const lenOk = words.length >= part7.minWords && words.length <= part7.maxWords;
    checks.push({
      name: "Word count (" + part7.minWords + "-" + part7.maxWords + ")",
      passed: lenOk,
      detail: "Actual words: " + words.length,
    });

    for (const anchor of part7.requiredAnchors || []) {
      const re = new RegExp(anchor.pattern, anchor.flags || "i");
      const ok = re.test(raw);
      checks.push({
        name: "Required: " + anchor.label,
        passed: ok,
        detail: ok ? "Matched" : "Missing pattern /" + anchor.pattern + "/",
      });
    }

    for (const forb of part7.forbiddenPatterns || []) {
      const re = new RegExp(forb.pattern, forb.flags || "i");
      const ok = !re.test(raw);
      checks.push({
        name: "Forbidden: " + forb.label,
        passed: ok,
        detail: ok ? "Clean" : "Matched forbidden pattern /" + forb.pattern + "/",
      });
    }

    if (Array.isArray(part7.acceptedExact) && part7.acceptedExact.length > 0) {
      const norm = normalizeText(raw, false);
      const exactHit = part7.acceptedExact.some((x) => normalizeText(x, false) === norm);
      if (exactHit) {
        return {
          passed: true,
          earned: part7.points,
          maxPoints: part7.points,
          details: ["Exact normalized reference match."],
          checks: checks.map((c) => ({ name: c.name, passed: true, detail: c.detail })),
        };
      }
    }

    const passedCount = checks.filter((c) => c.passed).length;
    const allPassed = passedCount === checks.length;
    const earned = Math.round((part7.points * passedCount) / checks.length * 100) / 100;
    return {
      passed: allPassed,
      earned: earned,
      maxPoints: part7.points,
      details: [passedCount + " / " + checks.length + " deterministic rule checks passed."],
      checks: checks,
    };
  }

  function checkLeanStatic(part7, code) {
    const cleaned = stripLeanComments(String(code || ""));
    const checks = [];
    const forbidden = part7.forbiddenTokens || ["sorry", "admit", "axiom", "unsafe", "implemented_by", "extern"];
    for (const tok of forbidden) {
      const re = new RegExp("\\b" + tok + "\\b");
      const ok = !re.test(cleaned);
      checks.push({
        name: "Forbid token: " + tok,
        passed: ok,
        detail: ok ? "Clean" : "Detected forbidden token " + tok,
      });
    }
    const normCode = cleaned.replace(/\s+/g, " ").trim();
    const normSig = String(part7.signature || "").replace(/\s+/g, " ").trim();
    const sigOk = normSig.length > 0 && normCode.includes(normSig);
    checks.push({
      name: "Exact theorem signature",
      passed: sigOk,
      detail: sigOk ? "Signature matched" : "Missing exact signature: " + normSig,
    });
    const bodyIndex = normCode.indexOf(normSig);
    let hasBody = false;
    if (sigOk && bodyIndex >= 0) {
      const tail = normCode.slice(bodyIndex + normSig.length).trim();
      hasBody = tail.length >= 2;
    }
    checks.push({
      name: "Non-empty proof body",
      passed: hasBody,
      detail: hasBody ? "Proof body present" : "Proof body is empty",
    });
    return checks;
  }

  function gradeLean4(part7, submission, externalReport) {
    const code = typeof submission === "string" ? submission : String((submission && submission.code) || "");
    const quickAnswers = submission && typeof submission === "object" ? submission.quickChecks || {} : {};
    const staticChecks = checkLeanStatic(part7, code);
    const staticOk = staticChecks.every((c) => c.passed);

    if (externalReport && externalReport.mode === "lean4" && externalReport.theoremName === part7.theoremName) {
      const verified = Boolean(externalReport.passed) && staticOk;
      return {
        passed: verified,
        earned: verified ? part7.points : 0,
        maxPoints: part7.points,
        details: [verified ? "Verified by Lean 4 CLI + anti-cheat." : "Lean 4 verification failed: " + (externalReport.message || "invalid proof")],
        checks: staticChecks.concat(externalReport.checks || []),
        externalVerified: verified,
      };
    }

    const quickList = Array.isArray(part7.quickChecks) ? part7.quickChecks : [];
    const quickResults = [];
    let quickPassed = 0;
    for (const qc of quickList) {
      const ans = normalizeText(quickAnswers[qc.id], false);
      const ok = (qc.accepted || []).some((a) => normalizeText(a, false) === ans);
      if (ok) {
        quickPassed += 1;
      }
      quickResults.push({
        name: "Quick check " + qc.id,
        passed: ok,
        detail: ok ? "Correct" : "Expected one of: " + (qc.accepted || []).join(" / "),
      });
    }

    const allChecks = staticChecks.concat(quickResults);
    const passedChecks = allChecks.filter((c) => c.passed).length;
    const allPassed = staticOk && (quickList.length === 0 || quickPassed === quickList.length);
    const earned = allChecks.length > 0 ? Math.round((part7.points * passedChecks) / allChecks.length * 100) / 100 : 0;
    return {
      passed: allPassed,
      earned: earned,
      maxPoints: part7.points,
      details: [
        staticOk
          ? "Static Lean 4 anti-cheat & signature check passed. Import CLI JSON for full kernel verification."
          : "Static Lean 4 anti-cheat or signature check failed.",
      ],
      checks: allChecks,
      externalVerified: false,
    };
  }

  function gradeExam(examData, answers, options) {
    const opts = options || {};
    const ans = answers || {};
    const items = [];
    const sectionStats = {};

    function record(partKey, itemMeta, earned, maxPoints, correct, userAnswer, expected, detail) {
      items.push({
        id: itemMeta.id,
        part: partKey,
        kp: itemMeta.kp,
        dimension: itemMeta.dimension,
        earned: earned,
        maxPoints: maxPoints,
        correct: correct,
        userAnswer: userAnswer,
        expected: expected,
        explanation: itemMeta.explanation,
        detail: detail || "",
      });
      if (!sectionStats[partKey]) {
        sectionStats[partKey] = { part: partKey, earned: 0, maxPoints: 0, correctCount: 0, totalCount: 0 };
      }
      sectionStats[partKey].earned += earned;
      sectionStats[partKey].maxPoints += maxPoints;
      sectionStats[partKey].totalCount += 1;
      if (correct) {
        sectionStats[partKey].correctCount += 1;
      }
    }

    const p1Ans = ans.part1 || {};
    for (const pair of examData.parts.part1.pairs) {
      const userVal = p1Ans[pair.id] || "";
      const ok = userVal === pair.rightId;
      record("part1", pair, ok ? pair.points : 0, pair.points, ok, userVal, pair.rightId);
    }

    const p2Ans = ans.part2 || {};
    for (const psg of examData.parts.part2.passages) {
      for (const q of psg.items) {
        const userVal = p2Ans[q.id] || "";
        const ok = userVal === q.answer;
        record("part2", q, ok ? q.points : 0, q.points, ok, userVal, q.answer);
      }
    }

    const p3Ans = ans.part3 || {};
    for (const q of examData.parts.part3.items) {
      const userVal = p3Ans[q.id] || "";
      const ok = userVal === q.answer;
      record("part3", q, ok ? q.points : 0, q.points, ok, userVal, q.answer);
    }

    const p4Ans = ans.part4 || {};
    for (const q of examData.parts.part4.items) {
      const userVal = p4Ans[q.id] || "";
      const ok = userVal === q.answer;
      record("part4", q, ok ? q.points : 0, q.points, ok, userVal, q.answer);
    }

    const p5Ans = ans.part5 || {};
    for (const q of examData.parts.part5.items) {
      const userVal = p5Ans[q.id] || "";
      const normUser = normalizeText(userVal, Boolean(q.caseSensitive));
      const ok = q.accepted.some((acc) => normalizeText(acc, Boolean(q.caseSensitive)) === normUser);
      record("part5", q, ok ? q.points : 0, q.points, ok, userVal, q.accepted.join(" / "));
    }

    const p6Ans = ans.part6 || {};
    for (const q of examData.parts.part6.items) {
      const userObj = p6Ans[q.id] || {};
      const userOp = String(userObj.op || "").trim().toLowerCase();
      const userFix = normalizeText(userObj.fix || "", Boolean(q.caseSensitive));
      const allowedFixes = Array.isArray(q.acceptedFixes) && q.acceptedFixes.length > 0 ? q.acceptedFixes : [q.fix];
      const opOk = userOp === q.op;
      const fixOk = q.op === "delete"
        ? (userFix === "" || allowedFixes.some((f) => normalizeText(f, Boolean(q.caseSensitive)) === userFix))
        : allowedFixes.some((f) => normalizeText(f, Boolean(q.caseSensitive)) === userFix);
      const ok = opOk && fixOk;
      record("part6", q, ok ? q.points : 0, q.points, ok, userObj, q.op + ": " + q.target + " -> " + q.fix);
    }

    const p7 = examData.parts.part7;
    let p7Res;
    if (p7.mode === "js-unit") {
      p7Res = gradeJsUnit(p7, ans.part7);
    } else if (p7.mode === "nl-rules") {
      p7Res = gradeNlRules(p7, ans.part7);
    } else {
      p7Res = gradeLean4(p7, ans.part7, opts.externalPart7 || null);
    }
    record("part7", p7, p7Res.earned, p7.points, p7Res.passed, ans.part7 || "", p7.referenceSolution, (p7Res.details || []).join(" "));

    const totalEarned = Math.round(items.reduce((s, x) => s + x.earned, 0) * 100) / 100;
    const totalMax = Math.round(items.reduce((s, x) => s + x.maxPoints, 0) * 100) / 100;
    const accuracy = totalMax > 0 ? Math.round((totalEarned / totalMax) * 1000) / 10 : 0;

    const dimensions = {};
    for (const dim of DIMENSIONS) {
      const subset = items.filter((x) => x.dimension === dim);
      const e = subset.reduce((s, x) => s + x.earned, 0);
      const m = subset.reduce((s, x) => s + x.maxPoints, 0);
      dimensions[dim] = {
        dimension: dim,
        earned: Math.round(e * 100) / 100,
        maxPoints: Math.round(m * 100) / 100,
        accuracy: m > 0 ? Math.round((e / m) * 1000) / 10 : 0,
        itemCount: subset.length,
      };
    }

    const kpIndex = {};
    for (const kp of examData.knowledgePoints) {
      kpIndex[kp.id] = kp;
    }
    const kpStats = {};
    for (const it of items) {
      if (!kpStats[it.kp]) {
        const meta = kpIndex[it.kp] || { id: it.kp, name: it.kp, dimension: it.dimension, remediation: "" };
        kpStats[it.kp] = {
          kp: it.kp,
          name: meta.name,
          dimension: meta.dimension,
          remediation: meta.remediation,
          earned: 0,
          maxPoints: 0,
          missedItems: [],
        };
      }
      kpStats[it.kp].earned += it.earned;
      kpStats[it.kp].maxPoints += it.maxPoints;
      if (!it.correct) {
        kpStats[it.kp].missedItems.push(it.id);
      }
    }

    const weaknessMap = Object.values(kpStats)
      .filter((k) => k.missedItems.length > 0)
      .map((k) => ({
        kp: k.kp,
        name: k.name,
        dimension: k.dimension,
        accuracy: k.maxPoints > 0 ? Math.round((k.earned / k.maxPoints) * 1000) / 10 : 0,
        missedCount: k.missedItems.length,
        missedItems: k.missedItems,
        remediation: k.remediation,
      }))
      .sort((a, b) => a.accuracy - b.accuracy || b.missedCount - a.missedCount);

    const patterns = [];
    const receptiveEarned = (sectionStats.part2 ? sectionStats.part2.earned : 0) + (sectionStats.part4 ? sectionStats.part4.earned : 0);
    const receptiveMax = (sectionStats.part2 ? sectionStats.part2.maxPoints : 0) + (sectionStats.part4 ? sectionStats.part4.maxPoints : 0);
    const receptiveAcc = receptiveMax > 0 ? (receptiveEarned / receptiveMax) * 100 : 0;
    const productiveEarned = (sectionStats.part5 ? sectionStats.part5.earned : 0) + (sectionStats.part7 ? sectionStats.part7.earned : 0);
    const productiveMax = (sectionStats.part5 ? sectionStats.part5.maxPoints : 0) + (sectionStats.part7 ? sectionStats.part7.maxPoints : 0);
    const productiveAcc = productiveMax > 0 ? (productiveEarned / productiveMax) * 100 : 0;

    if (receptiveAcc >= 75 && productiveAcc < 60) {
      patterns.push("Receptive-productive gap: strong comprehension in Reading/Cloze, but weaker active construction in Grammar Fill-in/Part VII.");
    }
    if (dimensions.lexicon.accuracy < 65) {
      patterns.push("Lexical retrieval bottleneck: reinforce form-meaning mapping in Part I before timed passages.");
    }
    if (dimensions.discourse.accuracy < 65) {
      patterns.push("Discourse cohesion deficit: practice structural transitions and logical flow in Part III (7-Choose-5).");
    }
    const p6Acc = sectionStats.part6 && sectionStats.part6.maxPoints > 0
      ? (sectionStats.part6.earned / sectionStats.part6.maxPoints) * 100
      : 100;
    if (p6Acc < 60) {
      patterns.push("Monitor gap: low accuracy in Part VI Error Correction indicates weak self-monitoring under local constraints.");
    }
    if (patterns.length === 0 && accuracy >= 85) {
      patterns.push("Balanced mastery across all four linguistic dimensions; ready to increase i+1 difficulty.");
    }

    return {
      meta: {
        examId: examData.meta.id,
        title: examData.meta.title,
        domain: examData.meta.domain,
        elapsedSeconds: Number(opts.elapsedSeconds || 0),
        gradedAt: new Date().toISOString(),
      },
      summary: {
        earned: totalEarned,
        maxPoints: totalMax,
        accuracy: accuracy,
      },
      sections: Object.values(sectionStats).map((s) => ({
        part: s.part,
        earned: Math.round(s.earned * 100) / 100,
        maxPoints: Math.round(s.maxPoints * 100) / 100,
        accuracy: s.maxPoints > 0 ? Math.round((s.earned / s.maxPoints) * 1000) / 10 : 0,
        correctCount: s.correctCount,
        totalCount: s.totalCount,
      })),
      dimensions: dimensions,
      weaknessMap: weaknessMap,
      patterns: patterns,
      part7Detail: p7Res,
      items: items,
    };
  }

  function buildGoldenAnswers(examData) {
    const out = {
      part1: {},
      part2: {},
      part3: {},
      part4: {},
      part5: {},
      part6: {},
      part7: examData.parts.part7.referenceSolution,
    };
    for (const pair of examData.parts.part1.pairs) {
      out.part1[pair.id] = pair.rightId;
    }
    for (const psg of examData.parts.part2.passages) {
      for (const q of psg.items) {
        out.part2[q.id] = q.answer;
      }
    }
    for (const q of examData.parts.part3.items) {
      out.part3[q.id] = q.answer;
    }
    for (const q of examData.parts.part4.items) {
      out.part4[q.id] = q.answer;
    }
    for (const q of examData.parts.part5.items) {
      out.part5[q.id] = q.accepted[0];
    }
    for (const q of examData.parts.part6.items) {
      out.part6[q.id] = { op: q.op, fix: q.fix };
    }
    if (examData.parts.part7.mode === "lean4") {
      const qcAns = {};
      for (const qc of examData.parts.part7.quickChecks || []) {
        qcAns[qc.id] = qc.accepted[0];
      }
      out.part7 = {
        code: examData.parts.part7.referenceSolution,
        quickChecks: qcAns,
      };
    }
    return out;
  }

  function buildWrongAnswers(examData) {
    const out = {
      part1: {},
      part2: {},
      part3: {},
      part4: {},
      part5: {},
      part6: {},
      part7: examData.parts.part7.negativeSolution,
    };
    const rids = examData.parts.part1.pairs.map((p) => p.rightId);
    examData.parts.part1.pairs.forEach((pair, idx) => {
      out.part1[pair.id] = rids[(idx + 1) % rids.length];
    });
    for (const psg of examData.parts.part2.passages) {
      for (const q of psg.items) {
        const wrongKey = Object.keys(q.options).find((k) => k !== q.answer);
        out.part2[q.id] = wrongKey;
      }
    }
    const allP3 = examData.parts.part3.options.map((o) => o.id);
    for (const q of examData.parts.part3.items) {
      out.part3[q.id] = allP3.find((id) => id !== q.answer);
    }
    for (const q of examData.parts.part4.items) {
      out.part4[q.id] = Object.keys(q.options).find((k) => k !== q.answer);
    }
    for (const q of examData.parts.part5.items) {
      out.part5[q.id] = "__wrong_answer__";
    }
    for (const q of examData.parts.part6.items) {
      const wrongOp = ["add", "delete", "replace"].find((o) => o !== q.op);
      out.part6[q.id] = { op: wrongOp, fix: "__wrong_fix__" };
    }
    if (examData.parts.part7.mode === "lean4") {
      const qcAns = {};
      for (const qc of examData.parts.part7.quickChecks || []) {
        qcAns[qc.id] = "__wrong__";
      }
      out.part7 = {
        code: examData.parts.part7.negativeSolution,
        quickChecks: qcAns,
      };
    }
    return out;
  }

  return {
    DIMENSIONS: DIMENSIONS,
    normalizeText: normalizeText,
    stripLeanComments: stripLeanComments,
    checkLeanStatic: checkLeanStatic,
    gradeJsUnit: gradeJsUnit,
    gradeNlRules: gradeNlRules,
    gradeLean4: gradeLean4,
    gradeExam: gradeExam,
    buildGoldenAnswers: buildGoldenAnswers,
    buildWrongAnswers: buildWrongAnswers,
  };
});
