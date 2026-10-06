#!/usr/bin/env node
// programmer-work-english/scripts/inversion-upload.mjs
//
// Stage-2 preparation helper (NO PUT / release / publish).
//
// Assembles a candidate draft that replaces the 32 original photos with their
// RGB-inverted counterparts, copying every non-identity field from the originals
// and preserving order and cover mapping.
//
// Policy:
//   * Uses the official PicLex CLI (runCLI) only; no direct DB writes, no source edits.
//   * Requires the fresh draft to contain exactly the 32 baseline originals from
//     workflow/inversion-current-before.json, unchanged in every protected field.
//   * Verifies images/<W>.png and images/inverted/<W>.png against
//     workflow/inversion-manifest.json.
//   * Uploads inverted images via `photos add` in serial batches <= 10, persisting
//     every returned {photoID, assetID} to workflow/inversion-upload-map.json after
//     each batch. Resumes from the map / draft filenames; never duplicates uploads.
//   * Writes workflow/inversion-candidate.json ({revision, draft}) for Root to PUT.
//
// Usage: node programmer-work-english/scripts/inversion-upload.mjs
import { createHash } from "node:crypto";
import { copyFile, mkdir, readFile, rename, stat, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TOPIC = path.dirname(HERE);
const WORKFLOW = path.join(TOPIC, "workflow");
const DECK = "121d190a-5d4c-4a09-8d50-4741acdbbb1b";
const DEFAULT_CLI =
  process.env.PICLEX_CLI ||
  path.join(os.homedir(), "github", "PicLex", "deck-workbench", "scripts", "workbench-cli.mjs");
const BATCH = 10;
const IDENTITY = new Set(["id", "assetID", "createdAt"]);
const INVERTED_RE = /^W(\d{3})-inverted-[0-9a-f]{8}\.png$/;

const paths = {
  baseline: path.join(WORKFLOW, "inversion-current-before.json"),
  manifest: path.join(WORKFLOW, "inversion-manifest.json"),
  map: path.join(WORKFLOW, "inversion-upload-map.json"),
  before: path.join(WORKFLOW, "inversion-upload-before.json"),
  candidate: path.join(WORKFLOW, "inversion-candidate.json"),
  cardMap: path.join(WORKFLOW, "inversion-card-map.json"),
  stage: path.join(WORKFLOW, "inversion-upload-stage"),
};

const now = () => new Date().toISOString();
const fail = (message) => {
  throw new Error(message);
};

async function sha256File(file) {
  return createHash("sha256").update(await readFile(file)).digest("hex");
}

async function loadJSON(file) {
  return JSON.parse(await readFile(file, "utf8"));
}

async function saveJSON(file, data) {
  await mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  await writeFile(tmp, `${JSON.stringify(data, null, 2)}\n`);
  await rename(tmp, file);
}

function deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a !== typeof b || a === null || b === null) return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) return a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  if (typeof a === "object")
    return (
      Object.keys(a).length === Object.keys(b).length &&
      Object.keys(a).every((k) => deepEqual(a[k], b[k]))
    );
  return false;
}

function protectedFields(card) {
  return Object.fromEntries(Object.entries(card).filter(([k]) => !IDENTITY.has(k)));
}

function protectedDiff(expected, actual) {
  const a = protectedFields(expected);
  const b = protectedFields(actual);
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  const diff = [];
  for (const key of keys) if (!deepEqual(a[key], b[key])) diff.push(key);
  return diff;
}

const widOf = (filename) => {
  const m = String(filename || "").match(/^(W\d{3})/);
  return m ? m[1] : null;
};

async function loadCLI() {
  const mod = await import(pathToFileURL(DEFAULT_CLI).href);
  if (typeof mod.runCLI !== "function") fail(`CLI 未导出 runCLI: ${DEFAULT_CLI}`);
  return mod.runCLI;
}

async function main() {
  const startedAt = now();
  const t0 = Date.now();
  const baseline = await loadJSON(paths.baseline);
  const manifest = await loadJSON(paths.manifest);
  const runCLI = await loadCLI();

  if (baseline.id !== DECK) fail(`baseline deckID 不匹配: ${baseline.id}`);
  if (baseline.draft.cards.length !== 32) fail("baseline 必须恰好 32 张原始卡");

  const manifestByWid = new Map(manifest.cards.map((c) => [c.card, c]));
  const baselineWids = [];
  for (const b of baseline.draft.cards) {
    const wid = widOf(b.filename);
    if (!wid) fail(`无法从 filename 解析卡片 ID: ${b.filename}`);
    baselineWids.push(wid);
    const m = manifestByWid.get(wid);
    if (!m) fail(`manifest 缺少 ${wid}`);
    const src = path.join(TOPIC, m.source);
    const inv = path.join(TOPIC, m.inverted);
    if (!existsSync(src) || !existsSync(inv)) fail(`${wid} 源图或反色图缺失`);
    if ((await sha256File(src)) !== m.sourceSHA256) fail(`${wid} 原图哈希与 manifest 不一致`);
    if ((await sha256File(inv)) !== m.invertedSHA256) fail(`${wid} 反色图哈希与 manifest 不一致`);
  }

  // Fresh draft + one-time pre-upload backup.
  let deck = await runCLI(["decks", "get", "--deck", DECK]);
  if (!existsSync(paths.before)) await saveJSON(paths.before, deck);

  // The 32 baseline originals must be present and byte-for-byte unchanged.
  const freshById = new Map(deck.draft.cards.map((c) => [c.id, c]));
  const baselineIds = new Set(baseline.draft.cards.map((c) => c.id));
  for (const b of baseline.draft.cards) {
    const f = freshById.get(b.id);
    if (!f) fail(`线上草稿缺少 baseline 原卡: ${b.filename}`);
    if (!deepEqual(f, b)) fail(`线上原卡已被修改: ${b.filename}`);
  }
  for (const c of deck.draft.cards) {
    if (baselineIds.has(c.id)) continue;
    if (INVERTED_RE.test(c.filename)) continue;
    fail(`出现未预期的额外卡片: ${c.filename}`);
  }

  // Upload map + recovery by draft filenames.
  const map = existsSync(paths.map)
    ? await loadJSON(paths.map)
    : { deckID: DECK, createdAtUTC: now(), cards: {} };
  map.cards ||= {};
  let recovered = 0;
  for (const c of deck.draft.cards) {
    const m = c.filename.match(INVERTED_RE);
    if (!m) continue;
    const wid = `W${m[1]}`;
    if (!map.cards[wid]) {
      map.cards[wid] = {
        wid,
        photoID: c.id,
        assetID: c.assetID,
        filename: c.filename,
        recoveredFromDraft: true,
        uploadedAtUTC: now(),
      };
      recovered += 1;
      await saveJSON(paths.map, map);
    }
  }

  const inDraft = new Set(deck.draft.cards.map((c) => c.id));
  const missing = baselineWids.filter(
    (wid) => !(map.cards[wid] && inDraft.has(map.cards[wid].photoID)),
  );

  const batches = [];
  let revision = deck.revision;
  await mkdir(paths.stage, { recursive: true });
  for (let i = 0; i < missing.length; i += BATCH) {
    const chunk = missing.slice(i, i + BATCH);
    const stageFiles = [];
    for (const wid of chunk) {
      const m = manifestByWid.get(wid);
      const name = `${wid}-inverted-${m.invertedSHA256.slice(0, 8)}.png`;
      const dest = path.join(paths.stage, name);
      if (!existsSync(dest) || (await sha256File(dest)) !== m.invertedSHA256)
        await copyFile(path.join(TOPIC, m.inverted), dest);
      stageFiles.push(dest);
    }
    const batchStart = Date.now();
    let result;
    try {
      result = await runCLI([
        "photos",
        "add",
        "--deck",
        DECK,
        "--revision",
        String(revision),
        ...stageFiles,
      ]);
    } catch (error) {
      await saveJSON(paths.map, map);
      fail(`上传批次失败（已保存 map，请先查询草稿再重试）：${error?.message ?? error}`);
    }
    for (const photo of result.photos ?? []) {
      const m = photo.filename.match(INVERTED_RE);
      if (!m) fail(`上传返回了非预期文件名: ${photo.filename}`);
      const wid = `W${m[1]}`;
      map.cards[wid] = {
        wid,
        photoID: photo.id,
        assetID: photo.assetID,
        filename: photo.filename,
        uploadedAtUTC: now(),
      };
    }
    revision = result.revision;
    await saveJSON(paths.map, map); // persist immediately after each batch
    batches.push({
      ids: chunk,
      revision,
      wallMs: Date.now() - batchStart,
      photoCount: (result.photos ?? []).length,
    });
  }

  // Re-read the freshest draft and assemble the candidate.
  deck = await runCLI(["decks", "get", "--deck", DECK]);
  const fresh = new Map(deck.draft.cards.map((c) => [c.id, c]));
  const candidateCards = [];
  const cardMap = [];
  const allDiffs = [];
  for (const b of baseline.draft.cards) {
    const wid = widOf(b.filename);
    const entry = map.cards[wid];
    if (!entry) fail(`缺少上传映射: ${wid}`);
    const uploaded = fresh.get(entry.photoID);
    if (!uploaded) fail(`上传卡不在最新草稿中: ${wid}`);
    const candidateCard = {
      id: uploaded.id,
      assetID: uploaded.assetID,
      createdAt: uploaded.createdAt,
      filename: b.filename,
      filenameEncoding: b.filenameEncoding,
      labels: b.labels,
      quote: b.quote,
      rights: b.rights,
      sourceURL: b.sourceURL,
    };
    candidateCards.push(candidateCard);
    const diff = protectedDiff(b, candidateCard);
    if (diff.length) allDiffs.push({ wid, diff });
    cardMap.push({
      wid,
      originalID: b.id,
      originalAssetID: b.assetID,
      newID: uploaded.id,
      newAssetID: uploaded.assetID,
      uploadFilename: uploaded.filename,
      finalFilename: b.filename,
      protectedDiff: diff,
    });
  }
  if (allDiffs.length) fail(`候选卡保护字段出现差异: ${JSON.stringify(allDiffs)}`);

  const coverIndex = baseline.draft.cards.findIndex((c) => c.id === baseline.draft.coverID);
  if (coverIndex < 0) fail("baseline coverID 不在卡片列表中");
  const candidateDraft = {
    ...deck.draft,
    coverID: candidateCards[coverIndex].id,
    cards: candidateCards,
  };
  await saveJSON(paths.candidate, { revision: deck.revision, draft: candidateDraft });
  await saveJSON(paths.cardMap, {
    deckID: DECK,
    generatedAtUTC: now(),
    originalCards: baseline.draft.cards.length,
    candidateCards: candidateCards.length,
    protectedDiff: allDiffs,
    cards: cardMap,
  });

  const summary = {
    deckID: DECK,
    startedAtUTC: startedAt,
    finishedAtUTC: now(),
    wallMs: Date.now() - t0,
    recoveredFromDraft: recovered,
    uploadedThisRun: missing.length,
    batches,
    mapPath: path.relative(TOPIC, paths.map),
    candidatePath: path.relative(TOPIC, paths.candidate),
    cardMapPath: path.relative(TOPIC, paths.cardMap),
    candidateCardCount: candidateCards.length,
    revisionForPut: deck.revision,
    protectedDiffCount: allDiffs.length,
  };
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error(`inversion-upload 失败: ${error?.message ?? error}`);
  process.exitCode = 1;
});
