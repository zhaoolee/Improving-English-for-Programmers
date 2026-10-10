#!/usr/bin/env node
// 程序员面试学习内容导入 runner（串行、幂等、可恢复、写入前严格预检）。
//
// 只准备，不执行：默认 --dry-run；真正写入必须显式 --execute。
// 复用 scene-cards-850/scripts/import-piclex.mjs 的 runImport；不修改旧 importer。
//
// 写入前预检（一次官方 decks get）：
//   - 40 个 photoID / 顺序 / coverID / isFree / productID / 照片数 与 pre-write-draft 一致；
//   - 每张 job.expectedAssetID 必须等于远端 assetID（既有 photoID + 当前 assetID）；
//   - 内容与 pre-write-draft 一致；已有本方 receipt 的卡，内容须与本方 annotations 的
//     importer patch 字段一致（filename/labels/quote/rights/sourceURL，含 labels 内 keyword/dialogue）；
//   - assetID 仅允许 7 张已替换卡取 effective-photo-mapping 的当前新值（按 filename 得到 cid）。
//   比较使用 importer 同款 providedEqual（递归、按 key，不受官方规范化键序影响）。
//   - 任何不一致立即停止（防止覆盖用户修改）；jobs 均带 photoID，禁止新的 photos add。
//
// check_failed 继续条件（全部满足才继续）：
//   - receipt.status === "check_failed" 且 checked 是非空数组；
//   - 每条错误严格匹配 /^第 (\d+) 张照片至少需要一个单词$/；
//   - 重新读取最新草稿，被点名的照片确实为空（无单词/无标注）。
// 任一不满足即停止；第二遍仅在第一遍完整跑完（未中断）时执行。
//
// 用法：
//   node run-learning-imports.mjs [--jobs-dir DIR] [--cli PATH] [--execute] [--report FILE]

import { readFile } from "node:fs/promises";
import { Readable } from "node:stream";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "..", "..");
const TOPIC = path.join(REPO, "programmer-interview");
const LEARN = path.join(TOPIC, "workflow", "learning-40-20261010");
const IMPORTER = path.join(REPO, "scene-cards-850", "scripts", "import-piclex.mjs");
const DEFAULT_JOBS = path.join(TOPIC, "piclex");
const DEFAULT_REPORT = path.join(LEARN, "import-run-report.json");
const PRE_WRITE = path.join(LEARN, "pre-write-draft.json");
const EFFECTIVE = path.join(LEARN, "effective-photo-mapping.json");
const REPLACE_IDS = new Set(["I003", "I005", "I007", "I013", "I017", "I028", "I038"]);
const IDS = Array.from({ length: 40 }, (_, i) => `I${String(i + 1).padStart(3, "0")}`);
const EMPTY_WORD_ERROR = /^第 (\d+) 张照片至少需要一个单词$/;
// importer loadAndValidate 真正写入的 patch 字段。
const PATCH_KEYS = ["filename", "labels", "quote", "rights", "sourceURL"];

function parseArgs(argv) {
  const out = { execute: false, jobsDir: DEFAULT_JOBS, cli: undefined,
    report: DEFAULT_REPORT, only: null };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--execute") out.execute = true;
    else if (a === "--jobs-dir") out.jobsDir = path.resolve(argv[++i]);
    else if (a === "--cli") out.cli = path.resolve(argv[++i]);
    else if (a === "--report") out.report = path.resolve(argv[++i]);
    else if (a === "--only") out.only = new Set(argv[++i].split(",").map((s) => s.trim()));
    else if (a === "--help" || a === "-h") {
      console.log("node run-learning-imports.mjs [--jobs-dir DIR] [--cli PATH] "
        + "[--execute] [--report FILE] [--only I003,I004]");
      process.exit(0);
    } else {
      console.error(`未知参数：${a}`);
      process.exit(2);
    }
  }
  return out;
}

const readJsonSafe = async (file) => {
  try { return JSON.parse(await readFile(file, "utf8")); } catch { return null; }
};

async function loadCLI(cliPath) {
  const mod = await import(pathToFileURL(cliPath).href);
  if (typeof mod.runCLI !== "function") throw new Error(`CLI 未导出 runCLI：${cliPath}`);
  return mod.runCLI;
}
const makeRun = (runCLI) =>
  (args) => runCLI(args, { stdin: Readable.from([]) });

// importer 同款递归比较：数组按长度+逐项，对象只比较 provided 提供的 key（键序无关）。
function providedEqual(remote, provided) {
  if (Array.isArray(provided)) {
    if (!Array.isArray(remote) || remote.length !== provided.length) return false;
    return provided.every((item, i) => providedEqual(remote[i], item));
  }
  if (provided && typeof provided === "object") {
    if (!remote || typeof remote !== "object" || Array.isArray(remote)) return false;
    return Object.keys(provided).every((k) => providedEqual(remote[k], provided[k]));
  }
  return remote === provided;
}

const cidOf = (card) => String(card?.filename ?? "").replace(/\.png$/i, "");

function importerPatch(ann, fallbackFilename) {
  const filename = typeof ann?.filename === "string" && ann.filename.trim()
    ? ann.filename : fallbackFilename;
  const patch = { labels: ann?.labels, quote: ann?.quote,
    rights: typeof ann?.rights === "string" ? ann.rights : "",
    sourceURL: typeof ann?.sourceURL === "string" ? ann.sourceURL : "" };
  if (filename) patch.filename = filename;
  return patch;
}

function cardMatchesAnnotations(card, ann, fallbackFilename) {
  return providedEqual(card, importerPatch(ann, fallbackFilename));
}

function preWriteContent(card) {
  const out = {};
  for (const key of PATCH_KEYS) out[key] = card[key];
  return out;
}

async function loadJobs(jobsDir, only) {
  const jobs = [];
  for (const id of IDS) {
    if (only && !only.has(id)) continue;
    const jobPath = path.join(jobsDir, `${id}_job.json`);
    const job = await readJsonSafe(jobPath);
    if (!job) throw new Error(`缺少 job 或不是有效 JSON：${jobPath}`);
    if (job.cardID !== id) throw new Error(`${jobPath} cardID=${job.cardID} 应为 ${id}`);
    if (typeof job.photoID !== "string" || !job.photoID)
      throw new Error(`${id} job 缺少 photoID（禁止重新上传）`);
    if (typeof job.expectedAssetID !== "string" || !job.expectedAssetID)
      throw new Error(`${id} job 缺少 expectedAssetID`);
    const annotations = await readJsonSafe(
      path.resolve(path.dirname(jobPath), job.annotationsPath));
    if (!annotations) throw new Error(`${id} annotations 缺失或无效`);
    jobs.push({ id, jobPath, job, annotations,
      photoID: job.photoID, assetID: job.expectedAssetID,
      receiptPath: path.resolve(path.dirname(jobPath), job.receiptPath) });
  }
  return jobs;
}

async function preflight(run, deckID, pre, effective, jobs) {
  const deck = await run(["decks", "get", "--deck", deckID]);
  const problems = [];
  if (deck.id !== pre.id) problems.push("deck id 不一致");
  if (deck.draft?.coverID !== pre.draft?.coverID) problems.push("coverID 不一致");
  if (deck.draft?.isFree !== pre.draft?.isFree) problems.push("isFree 不一致");
  if (deck.draft?.productID !== pre.draft?.productID) problems.push("productID 不一致");
  const rc = deck.draft?.cards ?? [];
  const pc = pre.draft?.cards ?? [];
  if (rc.length !== 40 || pc.length !== 40) problems.push("照片数不是 40");
  const byId = new Map(rc.map((c) => [c.id, c]));

  for (const spec of jobs) {
    const remote = byId.get(spec.job.photoID);
    if (!remote) { problems.push(`${spec.id} 目标 photoID 不在草稿中`); continue; }
    spec.photoID = remote.id;
    spec.assetID = remote.assetID;
    if (spec.job.expectedAssetID !== remote.assetID)
      problems.push(`${spec.id} job.expectedAssetID 与远端 assetID 不一致`);
  }

  for (let i = 0; i < Math.min(rc.length, pc.length); i += 1) {
    const cid = cidOf(pc[i]);
    if (rc[i].id !== pc[i].id) problems.push(`第 ${i + 1} 张 photoID/顺序不一致`);
    if (!providedEqual(rc[i], preWriteContent(pc[i]))) {
      const spec = jobs.find((j) => cidOf(j) === cid || j.job.photoID === rc[i].id);
      const receipt = spec ? await readJsonSafe(spec.receiptPath) : null;
      const ours = spec && receipt?.imageSHA256
        && cardMatchesAnnotations(rc[i], spec.annotations, pc[i].filename);
      if (!ours) problems.push(`${cid || rc[i].id} 内容与 pre-write-draft 不一致（疑似用户修改）`);
    }
    const eff = effective[cid];
    if (rc[i].assetID !== pc[i].assetID) {
      const allowed = REPLACE_IDS.has(cid) && eff && rc[i].assetID === eff.assetID;
      if (!allowed) problems.push(`${cid || rc[i].id} assetID 与 pre-write-draft 不一致`);
    }
  }
  return { deck, revision: deck.revision, problems, byId };
}

function validateCheckErrors(checked, deck) {
  if (!Array.isArray(checked) || checked.length === 0)
    return { ok: false, reason: "check_failed 的 checked 不是非空数组" };
  const byIndex = [];
  for (const err of checked) {
    const m = EMPTY_WORD_ERROR.exec(String(err));
    if (!m) return { ok: false, reason: `非预期的 check 错误：${err}` };
    const n = Number(m[1]);
    const card = (deck.draft?.cards ?? [])[n - 1];
    if (!card) return { ok: false, reason: `check 错误指向不存在的第 ${n} 张` };
    if ((card.labels ?? []).length !== 0)
      return { ok: false, reason: `第 ${n} 张并非空照片（已有 ${card.labels.length} 个词）` };
    byIndex.push(n);
  }
  return { ok: true, indices: byIndex };
}

async function runOne(runImport, spec, { dryRun, cli }) {
  const startedAt = new Date().toISOString();
  try {
    const summary = await runImport(spec.jobPath, { dryRun, cli });
    return { result: dryRun ? "dry_run" : (summary?.status ?? "done"),
      startedAt, finishedAt: new Date().toISOString(), summary };
  } catch (error) {
    const receipt = await readJsonSafe(spec.receiptPath);
    return { result: receipt?.status ?? "error",
      startedAt, finishedAt: new Date().toISOString(),
      error: String(error?.message ?? error).slice(0, 500), receipt };
  }
}

function summarize(entry, spec) {
  return {
    result: entry.result,
    photoID: spec?.photoID ?? entry.summary?.photoID ?? entry.receipt?.photoID ?? null,
    assetID: spec?.assetID ?? entry.summary?.assetID ?? entry.receipt?.assetID ?? null,
    timings: entry.summary?.timings ?? entry.receipt?.timings ?? null,
    checked: entry.summary?.checked ?? entry.receipt?.checked ?? null,
    error: entry.error ?? null,
    startedAt: entry.startedAt,
    finishedAt: entry.finishedAt,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { runImport, DEFAULT_CLI } = await import(pathToFileURL(IMPORTER).href);
  const cliPath = args.cli ?? DEFAULT_CLI;
  const run = makeRun(await loadCLI(cliPath));
  const pre = await readJsonSafe(PRE_WRITE);
  const effective = await readJsonSafe(EFFECTIVE);
  const jobs = await loadJobs(args.jobsDir, args.only);
  const deckID = jobs[0].job.deckID;

  const report = {
    startedAtUTC: new Date().toISOString(),
    dryRun: !args.execute,
    jobsDir: args.jobsDir,
    deckID,
    cardCount: jobs.length,
    preflight: null,
    pass1: {},
    pass2: {},
    summary: { done: [], checkFailedPersisted: [], stillFailed: [],
      skippedDone: [], dryRun: [] },
    note: "",
  };

  const dryRun = !args.execute;
  let flight = null;
  if (dryRun) {
    report.preflight = { skipped: "dry-run 只做本地校验，不访问服务。" };
  } else {
    flight = await preflight(run, deckID, pre, effective, jobs);
    report.preflight = { revision: flight.revision, problems: flight.problems };
    if (flight.problems.length) {
      report.note = "写入前预检失败，已停止（不覆盖用户修改）。";
      report.summary.stillFailed = flight.problems.map((p) => ({ id: "preflight", error: p }));
      return finish(args, report, 2);
    }
  }

  report.note = dryRun
    ? "dry-run：仅本地校验与计划；加 --execute 才连接官方并写入。"
    : "先写内容（check 可因其它卡缺失而 check_failed），最后幂等 read/check 刷新 done。";

  let interrupted = false;
  const stop = (id, entry) => {
    report.summary.stillFailed.push({ id, result: entry.result, error: entry.error ?? null });
    interrupted = true;
  };

  for (const spec of jobs) {
    const receipt = await readJsonSafe(spec.receiptPath);
    if (!dryRun && receipt?.status === "done"
      && cardMatchesAnnotations(flight.byId.get(spec.photoID), spec.annotations, `${spec.id}.png`)) {
      report.summary.skippedDone.push(spec.id);
      continue;
    }
    const entry = await runOne(runImport, spec, { dryRun, cli: cliPath });
    report.pass1[spec.id] = summarize(entry, spec);
    if (entry.result === "done") { report.summary.done.push(spec.id); continue; }
    if (entry.result === "dry_run") { report.summary.dryRun.push(spec.id); continue; }
    if (entry.result === "check_failed") {
      const fresh = await run(["decks", "get", "--deck", deckID]);
      const verdict = validateCheckErrors(entry.receipt?.checked, fresh);
      if (verdict.ok) { report.summary.checkFailedPersisted.push(spec.id); continue; }
      report.pass1[spec.id].error = verdict.reason;
      stop(spec.id, { result: "check_failed_invalid", error: verdict.reason });
      break;
    }
    stop(spec.id, entry);
    break;
  }

  if (!dryRun && !interrupted) {
    const pending = jobs.filter((j) => report.pass1[j.id]?.result === "check_failed");
    for (const spec of pending) {
      const entry = await runOne(runImport, spec, { dryRun, cli: cliPath });
      report.pass2[spec.id] = summarize(entry, spec);
      if (entry.result === "done") {
        report.summary.done.push(spec.id);
        report.summary.checkFailedPersisted =
          report.summary.checkFailedPersisted.filter((x) => x !== spec.id);
      } else {
        stop(spec.id, entry);
        break;
      }
    }
  } else if (interrupted) {
    report.note += " 第一遍中断，未执行第二遍。";
  }

  report.summary.done = [...new Set(report.summary.done)];
  report.summary.checkFailedPersisted = [...new Set(report.summary.checkFailedPersisted)];
  return finish(args, report, report.summary.stillFailed.length ? 1 : 0);
}

async function finish(args, report, code) {
  report.finishedAtUTC = new Date().toISOString();
  const fs = await import("node:fs/promises");
  await fs.mkdir(path.dirname(args.report), { recursive: true });
  await fs.writeFile(args.report, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`runner ${report.dryRun ? "dry-run" : "execute"}：jobs=${report.cardCount} `
    + `done=${report.summary.done.length} `
    + `check_failed=${report.summary.checkFailedPersisted.length} `
    + `skipped_done=${report.summary.skippedDone.length} `
    + `failed=${report.summary.stillFailed.length}`);
  console.log(`report: ${args.report}`);
  return code;
}

try {
  process.exit(await main());
} catch (error) {
  console.error(`runner 拒绝继续：${error?.message ?? error}`);
  process.exit(2);
}
