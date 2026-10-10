#!/usr/bin/env node
// 用官方 runCLI 按序替换 7 张已修图（I003 I005 I007 I013 I017 I028 I038）。
//
// 只准备，不执行：默认 --dry-run；真正替换必须显式 --execute（由 Root 执行）。
// 只调用官方 `photos replace`：不上传新 photo、不删 photo、不直写数据库、不猜 SHA 当 assetID。
//
// 每次替换前：
//   - 先把已有回执的 newAssetID 合并进 expectedDoc，再与最新 decks get 对照
//     （仅这 7 张的 assetID 允许变化，其余照片内容/顺序/photoID/coverID/isFree/productID 完全不变）；
//   - 目标图片当前 SHA256 必须等于 effective-photo-mapping 的 sourceSHA256。
// 成功条件：官方返回 photo.id 严格等于原 card.id、filename 同名、且除 assetID 外整对象不变；
//           成功后立即写 image-replacement-receipts/Ixxx.json 并立即刷新 effective mapping。
// 失败后：立即读最新状态并记录，不自动重试。
// 全部完成后：重读确认 40 卡只有 7 个 assetID 变化，保存 after-image-replacement-draft.json + replacements.json。
//
// 用法：
//   node replace-reviewed-images.mjs [--cli PATH] [--execute] [--report FILE]

import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { Readable } from "node:stream";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "..", "..");
const TOPIC = path.join(REPO, "programmer-interview");
const LEARN = path.join(TOPIC, "workflow", "learning-40-20261010");
const IMAGES = path.join(TOPIC, "images");
const IMPORTER = path.join(REPO, "scene-cards-850", "scripts", "import-piclex.mjs");
const PRE_WRITE = path.join(LEARN, "pre-write-draft.json");
const EFFECTIVE = path.join(LEARN, "effective-photo-mapping.json");
const RECEIPTS = path.join(LEARN, "image-replacement-receipts");
const SUMMARY = path.join(LEARN, "replacements.json");
const AFTER = path.join(LEARN, "after-image-replacement-draft.json");
const REPLACE_IDS = ["I003", "I005", "I007", "I013", "I017", "I028", "I038"];
const REPLACE_SET = new Set(REPLACE_IDS);

function parseArgs(argv) {
  const out = { execute: false, cli: undefined, report: SUMMARY,
    recomputeFinalCheck: false };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--execute") out.execute = true;
    else if (a === "--recompute-final-check") out.recomputeFinalCheck = true;
    else if (a === "--cli") out.cli = path.resolve(argv[++i]);
    else if (a === "--report") out.report = path.resolve(argv[++i]);
    else if (a === "--help" || a === "-h") {
      console.log("node replace-reviewed-images.mjs [--cli PATH] [--execute] "
        + "[--report FILE] [--recompute-final-check]");
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
const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");

async function loadCLI(cliPath) {
  const mod = await import(pathToFileURL(cliPath).href);
  if (typeof mod.runCLI !== "function") throw new Error(`CLI 未导出 runCLI：${cliPath}`);
  return mod.runCLI;
}
const makeRun = (runCLI) =>
  (args) => runCLI(args, { stdin: Readable.from([]) });

function contentSig(card) {
  return JSON.stringify({
    id: card.id, createdAt: card.createdAt, filenameEncoding: card.filenameEncoding,
    labels: card.labels ?? [], quote: card.quote ?? null,
    rights: card.rights ?? "", sourceURL: card.sourceURL ?? "",
  });
}

// filename(Ixxx.png) → I编号；用于最终对比，避免把 photo UUID 当 I 编号。
const cidOf = (card) => String(card?.filename ?? "").replace(/\.png$/i, "");

// 递归排序键，避免键序差异；忽略任意层级的 assetID。
function canon(value) {
  if (Array.isArray(value)) return value.map(canon);
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      if (key === "assetID") continue;
      out[key] = canon(value[key]);
    }
    return out;
  }
  return value;
}

function assertOnlyAssetChanged(original, returned) {
  if (!returned) throw new Error("replace 响应缺少 photo");
  if (returned.id !== original.id)
    throw new Error(`replace 返回 photoID ${returned.id} 不等于原 card.id ${original.id}`);
  if (returned.filename !== original.filename)
    throw new Error(`replace 返回文件名 ${returned.filename} 与原卡 ${original.filename} 不同`);
  if (JSON.stringify(canon(original)) !== JSON.stringify(canon(returned)))
    throw new Error("replace 返回照片除 assetID 外与原卡不一致");
}

function compareLatest(latest, expectedDoc) {
  const problems = [];
  if (latest.id !== expectedDoc.id) problems.push("deck id 不一致");
  if (latest.draft?.coverID !== expectedDoc.draft?.coverID) problems.push("coverID 不一致");
  if (latest.draft?.isFree !== expectedDoc.draft?.isFree) problems.push("isFree 不一致");
  if (latest.draft?.productID !== expectedDoc.draft?.productID)
    problems.push("productID 不一致");
  const rc = latest.draft?.cards ?? [];
  const ec = expectedDoc.draft?.cards ?? [];
  if (rc.length !== ec.length) problems.push("照片数不一致");
  for (let i = 0; i < Math.min(rc.length, ec.length); i += 1) {
    if (rc[i].id !== ec[i].id) problems.push(`第 ${i + 1} 张 photoID/顺序不一致`);
    if (rc[i].filename !== ec[i].filename) problems.push(`${rc[i].id} filename 不一致`);
    if (rc[i].assetID !== ec[i].assetID) problems.push(`${rc[i].id} assetID 与预期不一致`);
    if (contentSig(rc[i]) !== contentSig(ec[i])) problems.push(`${rc[i].id} 内容被改动`);
  }
  return problems;
}

function verifyFinal(pre, finalDoc) {
  const problems = [];
  const changed = [];
  if (finalDoc.id !== pre.id) problems.push("deck id 变化");
  if (finalDoc.draft?.coverID !== pre.draft?.coverID) problems.push("coverID 变化");
  if (finalDoc.draft?.isFree !== pre.draft?.isFree) problems.push("isFree 变化");
  if (finalDoc.draft?.productID !== pre.draft?.productID) problems.push("productID 变化");
  const fc = finalDoc.draft?.cards ?? [];
  const pc = pre.draft?.cards ?? [];
  if (fc.length !== 40 || pc.length !== 40) problems.push("照片数不是 40");
  for (let i = 0; i < Math.min(fc.length, pc.length); i += 1) {
    if (fc[i].id !== pc[i].id) problems.push(`第 ${i + 1} 张 photoID/顺序变化`);
    if (fc[i].filename !== pc[i].filename) problems.push(`${fc[i].id} filename 变化`);
    if (contentSig(fc[i]) !== contentSig(pc[i])) problems.push(`${fc[i].id} 内容变化`);
    if (fc[i].assetID !== pc[i].assetID) changed.push(cidOf(fc[i]));
  }
  const changedSet = [...new Set(changed)].sort();
  if (changedSet.join(",") !== [...REPLACE_SET].sort().join(","))
    problems.push(`assetID 变化集合不是 7 张：${changedSet.join(",")}`);
  return { changedAssetIDs: changedSet, problems };
}

async function persistJson(file, data) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(data, null, 2)}\n`);
}

function updateExpected(expectedDoc, cid, assetID) {
  const card = (expectedDoc.draft.cards ?? []).find((c) => c.filename === `${cid}.png`);
  if (card) card.assetID = assetID;
}

function refreshEffective(effective, cid, newAssetID, oldAssetID) {
  const entry = effective[cid] || (effective[cid] = {});
  entry.assetID_before_replace = entry.assetID_before_replace ?? oldAssetID;
  entry.assetID = newAssetID;
  entry.replacedAtUTC = new Date().toISOString();
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  // 离线：仅从已保存的 pre/after 草稿重算 finalCheck，不联网、不重换图。
  if (args.recomputeFinalCheck) {
    const pre = await readJsonSafe(PRE_WRITE);
    const after = await readJsonSafe(AFTER);
    if (!pre || !after) throw new Error("缺少 pre-write-draft.json 或 after-image-replacement-draft.json");
    const summary = await readJsonSafe(SUMMARY) || {};
    summary.finalCheck = verifyFinal(pre, after);
    summary.finalCheckRecomputedAtUTC = new Date().toISOString();
    summary.finalCheckNote = "由 replace-reviewed-images.mjs --recompute-final-check 从已保存草稿离线重算；按 filename 去 .png 比较 I 编号。";
    await persistJson(args.report, summary);
    console.log(`finalCheck(recomputed)：changed=${summary.finalCheck.changedAssetIDs.join(",")} problems=${summary.finalCheck.problems.length}`);
    return summary.finalCheck.problems.length ? 1 : 0;
  }

  const { DEFAULT_CLI } = await import(pathToFileURL(IMPORTER).href);
  const runCLI = await loadCLI(args.cli ?? DEFAULT_CLI);
  const run = makeRun(runCLI);
  const pre = await readJsonSafe(PRE_WRITE);
  const effective = await readJsonSafe(EFFECTIVE);
  const deckID = pre.id;
  const expectedDoc = JSON.parse(JSON.stringify(pre));

  const report = {
    startedAtUTC: new Date().toISOString(),
    dryRun: !args.execute,
    deckID,
    replaced: [],
    reused: [],
    failed: [],
    problems: [],
    finalCheck: null,
    note: args.execute
      ? "逐张官方 photos replace；成功立即写回执与 effective mapping；失败即记录不重试。"
      : "dry-run：只读取/校验，不替换。",
  };

  for (const cid of REPLACE_IDS) {
    const imagePath = path.join(IMAGES, `${cid}.png`);
    const selectedSHA = sha256(await readFile(imagePath));
    const eff = effective[cid];
    if (eff?.sourceSHA256 !== selectedSHA) {
      report.failed.push({ cardID: cid, error: "本地图片哈希与 effective mapping 不一致" });
      break;
    }
    const receiptPath = path.join(RECEIPTS, `${cid}.json`);
    const existing = await readJsonSafe(receiptPath);
    // 已有回执的 newAssetID 先合并进 expectedDoc，续跑才不会把自己的新图判成冲突。
    if (existing?.newAssetID) {
      updateExpected(expectedDoc, cid, existing.newAssetID);
      refreshEffective(effective, cid, existing.newAssetID, existing.oldAssetID);
    }

    const latest = await run(["decks", "get", "--deck", deckID]);
    const problems = compareLatest(latest, expectedDoc);
    if (problems.length) { report.problems.push({ cardID: cid, problems }); break; }
    const card = (latest.draft.cards ?? []).find((c) => c.filename === `${cid}.png`);
    if (!card) { report.problems.push({ cardID: cid, problems: ["找不到目标照片"] }); break; }

    // 已有替换回执且工作台与它相等 → 复用不重写。
    if (existing?.newAssetID && card.assetID === existing.newAssetID) {
      report.reused.push({ cardID: cid, photoID: card.id, assetID: card.assetID });
      refreshEffective(effective, cid, card.assetID, existing.oldAssetID);
      if (args.execute) await persistJson(EFFECTIVE, effective);
      continue;
    }

    if (!args.execute) {
      report.replaced.push({ cardID: cid, planned: true, photoID: card.id,
        oldAssetID: card.assetID, selectedSourceSHA256: selectedSHA });
      updateExpected(expectedDoc, cid, card.assetID);
      continue;
    }

    const startedAtUTC = new Date().toISOString();
    try {
      const result = await run(["photos", "replace", "--deck", deckID,
        "--photo", card.id, "--revision", String(latest.revision), "--file", imagePath]);
      const returned = result?.photo;
      assertOnlyAssetChanged(card, returned);
      const receipt = {
        cardID: cid, photoID: returned.id, filename: returned.filename,
        oldAssetID: card.assetID, newAssetID: returned.assetID,
        selectedSourceSHA256: selectedSHA, revision: result.revision,
        startedAtUTC, finishedAtUTC: new Date().toISOString(), status: "replaced",
        photo: { id: returned.id, assetID: returned.assetID,
          filename: returned.filename, createdAt: returned.createdAt },
        command: "photos replace",
      };
      await persistJson(receiptPath, receipt);
      report.replaced.push({ cardID: cid, ...receipt });
      updateExpected(expectedDoc, cid, returned.assetID);
      refreshEffective(effective, cid, returned.assetID, card.assetID);
      await persistJson(EFFECTIVE, effective); // 每卡成功后立即写回
    } catch (error) {
      const after = await run(["decks", "get", "--deck", deckID]);
      const observed = (after.draft?.cards ?? []).find((c) => c.filename === `${cid}.png`);
      const receipt = {
        cardID: cid, status: "failed", startedAtUTC,
        finishedAtUTC: new Date().toISOString(),
        error: String(error?.message ?? error).slice(0, 500),
        observed: observed ? { photoID: observed.id, assetID: observed.assetID } : null,
        selectedSourceSHA256: selectedSHA,
      };
      await persistJson(receiptPath, receipt);
      report.failed.push({ cardID: cid, error: receipt.error, observed: receipt.observed });
      break; // 不自动重试
    }
  }

  if (args.execute) {
    const finalDoc = await run(["decks", "get", "--deck", deckID]);
    await persistJson(AFTER, finalDoc);
    report.finalCheck = verifyFinal(pre, finalDoc);
  }

  report.finishedAtUTC = new Date().toISOString();
  await persistJson(args.report, report);
  console.log(`replace ${report.dryRun ? "dry-run" : "execute"}：`
    + `replaced=${report.replaced.length} reused=${report.reused.length} `
    + `failed=${report.failed.length} problems=${report.problems.length} `
    + `final=${report.finalCheck ? report.finalCheck.problems.length + " problems" : "n/a"}`);
  console.log(`report: ${args.report}`);
  return report.failed.length || report.problems.length
    || (report.finalCheck?.problems.length ?? 0) ? 1 : 0;
}

try {
  process.exit(await main());
} catch (error) {
  console.error(`replace 拒绝继续：${error?.message ?? error}`);
  process.exit(2);
}
