#!/usr/bin/env node
// 单图 PicLex 快速导入器。
//
// 用法：
//   node import-piclex.mjs --job manifest.json [--dry-run] [--cli /path/to/workbench-cli.mjs]
//
// 复用官方 workbench CLI 的 runCLI（进程内调用，不 spawn 子进程），
// 单张图片从校验到 check 一次跑完，失败可凭回执续跑。
import { parseArgs, isDeepStrictEqual } from "node:util";
import { createHash, randomBytes } from "node:crypto";
import {
  readFile,
  stat,
  mkdir,
  mkdtemp,
  copyFile,
  writeFile,
  rename,
  rm,
} from "node:fs/promises";
import { Readable } from "node:stream";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const DEFAULT_CLI =
  process.env.PICLEX_CLI ||
  path.join(
    os.homedir(),
    "github",
    "PicLex",
    "deck-workbench",
    "scripts",
    "workbench-cli.mjs",
  );
const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const IMAGE_EXTENSIONS = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".heic",
  ".heif",
]);
const HEX64 = /^[0-9a-fA-F]{64}$/;
const MAX_TEXT_SAMPLE = 400;

class ImportError extends Error {
  constructor(message) {
    super(message);
    this.name = "ImportError";
  }
}
const fail = (message) => {
  throw new ImportError(message);
};

const sha256 = (buffer) => createHash("sha256").update(buffer).digest("hex");
const now = () => Date.now();

// ---------------------------------------------------------------------------
// JSON Schema（由 runCLI schema 返回）最小校验器：只覆盖 CLI 实际输出的关键字。
// ---------------------------------------------------------------------------
function typeOf(value) {
  if (Array.isArray(value)) return "array";
  if (value === null) return "null";
  return typeof value;
}

function validateSchema(value, schema, at, errors) {
  if (!schema || typeof schema !== "object") return;
  if (Array.isArray(schema.anyOf)) {
    const ok = schema.anyOf.some(
      (branch) => schemaErrors(value, branch, at).length === 0,
    );
    if (!ok) {
      errors.push(`${at} 不满足允许的 JSON 格式`);
      return;
    }
  }
  if (schema.const !== undefined && value !== schema.const)
    errors.push(`${at} 必须为 ${JSON.stringify(schema.const)}`);
  if (Array.isArray(schema.enum) && !schema.enum.includes(value))
    errors.push(`${at} 取值不在允许范围`);
  if (schema.type !== undefined) {
    const actual = typeOf(value);
    const ok =
      schema.type === "integer"
        ? Number.isInteger(value)
        : schema.type === "number"
          ? typeof value === "number" && Number.isFinite(value)
          : actual === schema.type;
    if (!ok) {
      errors.push(`${at} 类型应为 ${schema.type}，实际为 ${actual}`);
      return;
    }
  }
  if (typeof value === "string") {
    if (schema.maxLength !== undefined && value.length > schema.maxLength)
      errors.push(`${at} 文本长度不能超过 ${schema.maxLength}`);
    if (schema.minLength !== undefined && value.length < schema.minLength)
      errors.push(`${at} 文本长度不能少于 ${schema.minLength}`);
    if (schema.pattern && !new RegExp(schema.pattern).test(value))
      errors.push(`${at} 格式不符合 ${schema.pattern}`);
    if (
      schema.format === "uri" &&
      !/^https?:\/\//.test(value)
    )
      errors.push(`${at} 必须是 http(s) 链接`);
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    if (schema.minimum !== undefined && value < schema.minimum)
      errors.push(`${at} 不能小于 ${schema.minimum}`);
    if (schema.maximum !== undefined && value > schema.maximum)
      errors.push(`${at} 不能大于 ${schema.maximum}`);
  }
  if (Array.isArray(value) && schema.items)
    value.forEach((item, i) =>
      validateSchema(item, schema.items, `${at}[${i}]`, errors),
    );
  if (value && typeof value === "object" && !Array.isArray(value)) {
    for (const key of schema.required ?? [])
      if (value[key] === undefined) errors.push(`${at}.${key} 为必填`);
    for (const [key, sub] of Object.entries(schema.properties ?? {}))
      if (value[key] !== undefined)
        validateSchema(value[key], sub, `${at}.${key}`, errors);
  }
}

function schemaErrors(value, schema, at) {
  const errors = [];
  validateSchema(value, schema, at, errors);
  return errors;
}

// ---------------------------------------------------------------------------
// job 读取与路径解析
// ---------------------------------------------------------------------------
function resolveJob(job, jobDir) {
  const resolve = (value, name) => {
    if (typeof value !== "string" || !value.trim())
      fail(`job.${name} 必须是非空字符串`);
    return path.resolve(jobDir, value);
  };
  return {
    imagePath: resolve(job.imagePath, "imagePath"),
    annotationsPath: resolve(job.annotationsPath, "annotationsPath"),
    receiptPath: resolve(job.receiptPath, "receiptPath"),
  };
}

function validateJobShape(job) {
  if (!job || typeof job !== "object" || Array.isArray(job))
    fail("job 必须是 JSON 对象");
  for (const key of ["cardID", "deckID"])
    if (typeof job[key] !== "string" || !job[key].trim())
      fail(`job.${key} 必须是非空字符串`);
  if (job.imageReviewed !== true) fail("job.imageReviewed 必须为 true");
  if (typeof job.imageSHA256 !== "string" || !HEX64.test(job.imageSHA256))
    fail("job.imageSHA256 必须是 64 位十六进制字符串");
  if (!Array.isArray(job.expectedWords) || job.expectedWords.length === 0)
    fail("job.expectedWords 必须是非空数组");
  for (const word of job.expectedWords)
    if (typeof word !== "string" || !word.trim())
      fail("job.expectedWords 只能包含非空英文词");
  if (new Set(job.expectedWords).size !== job.expectedWords.length)
    fail("job.expectedWords 存在重复词");
  if (
    job.photoID !== undefined &&
    (typeof job.photoID !== "string" || !job.photoID.trim())
  )
    fail("job.photoID 必须是非空字符串");
  if (
    job.expectedAssetID !== undefined &&
    !/^[0-9a-f]{64}$/.test(job.expectedAssetID)
  )
    fail("job.expectedAssetID 必须是 64 位小写十六进制字符串");
}

// ---------------------------------------------------------------------------
// 几何校验（0–1000、正面积、指向点在框内、positionUnavailable 无框无点）
// ---------------------------------------------------------------------------
const inRange = (v) =>
  typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 1000;
const intInRange = (v) => Number.isInteger(v) && v >= 0 && v <= 1000;

function checkPoint(point, name) {
  if (!point || typeof point !== "object" || Array.isArray(point))
    fail(`${name} 必须是坐标对象`);
  if (!inRange(point.x) || !inRange(point.y))
    fail(`${name} 的 x/y 必须在 0 到 1000 之间`);
}

function checkBox(box, name) {
  if (!box || typeof box !== "object" || Array.isArray(box))
    fail(`${name} 必须是框对象`);
  for (const key of ["left", "top", "right", "bottom"])
    if (!intInRange(box[key]))
      fail(`${name}.${key} 必须是 0 到 1000 的整数`);
  if (!(box.right > box.left && box.bottom > box.top))
    fail(`${name} 必须有正的宽度和高度`);
}

function validateGeometry(label, index) {
  const at = `labels[${index}]`;
  if (!intInRange(label.x) || !intInRange(label.y))
    fail(`${at} 的 x/y 必须是 0 到 1000 的整数`);
  const unavailable = label.positionUnavailable === true;
  const hasBox = label.boundingBox !== undefined && label.boundingBox !== null;
  const hasAnchor =
    label.anchorPosition !== undefined && label.anchorPosition !== null;
  if (label.bubblePosition !== undefined && label.bubblePosition !== null)
    checkPoint(label.bubblePosition, `${at}.bubblePosition`);
  if (hasAnchor) checkPoint(label.anchorPosition, `${at}.anchorPosition`);
  if (hasBox) checkBox(label.boundingBox, `${at}.boundingBox`);
  if (unavailable && (hasBox || hasAnchor))
    fail(`${at} 在 positionUnavailable=true 时不能有框或指向点`);
  if (hasBox && hasAnchor) {
    const { left, top, right, bottom } = label.boundingBox;
    const { x, y } = label.anchorPosition;
    if (x < left || x > right || y < top || y > bottom)
      fail(`${at} 的指向点必须在框内`);
  }
}

// ---------------------------------------------------------------------------
// 本地校验 + 加载素材（任何网络写入之前完成）
// ---------------------------------------------------------------------------
async function loadAndValidate(job, resolved, cliFn) {
  const imageInfo = await stat(resolved.imagePath).catch((error) => {
    if (error.code === "ENOENT") fail(`图片不存在：${resolved.imagePath}`);
    throw error;
  });
  if (!imageInfo.isFile()) fail("imagePath 必须是普通文件");
  if (imageInfo.size <= 0 || imageInfo.size > MAX_IMAGE_BYTES)
    fail("图片必须大于 0 字节且不超过 20 MB");
  const imageBytes = await readFile(resolved.imagePath);
  const imageSHA256 = sha256(imageBytes);
  if (imageSHA256 !== job.imageSHA256.toLowerCase())
    fail("原始图片 SHA256 与 job.imageSHA256 严格不匹配");
  const ext = path.extname(resolved.imagePath);
  if (!IMAGE_EXTENSIONS.has(ext.toLowerCase()))
    fail("图片扩展名必须是 JPG、JPEG、PNG、WebP 或 HEIC");

  let annotationsText;
  try {
    annotationsText = await readFile(resolved.annotationsPath, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") fail(`标注不存在：${resolved.annotationsPath}`);
    throw error;
  }
  let annotations;
  try {
    annotations = JSON.parse(annotationsText);
  } catch {
    fail("标注文件不是有效 JSON");
  }
  if (!annotations || typeof annotations !== "object" || Array.isArray(annotations))
    fail("标注文件必须是 JSON 对象");
  if (!Array.isArray(annotations.labels) || annotations.labels.length === 0)
    fail("标注必须包含非空 labels 数组");

  const labels = annotations.labels;
  const english = labels.map((label) =>
    label && typeof label.english === "string" ? label.english : undefined,
  );
  if (english.length !== job.expectedWords.length)
    fail("expectedWords 与 labels 英文数量不一致");
  for (let i = 0; i < english.length; i += 1) {
    if (english[i] !== job.expectedWords[i])
      fail(
        `expectedWords 与 labels 英文顺序不一致：第 ${i + 1} 个应为 ${job.expectedWords[i]}，实际 ${english[i]}`,
      );
  }
  if (new Set(english).size !== english.length)
    fail("labels 英文存在重复词");

  labels.forEach((label, index) => {
    if (!label || typeof label !== "object" || Array.isArray(label))
      fail(`labels[${index}] 必须是对象`);
    if (typeof label.english !== "string" || !label.english.trim())
      fail(`labels[${index}].english 不能为空`);
    if (typeof label.chinese !== "string" || !label.chinese.trim())
      fail(`labels[${index}].chinese 不能为空`);
    validateGeometry(label, index);
  });

  const quote = annotations.quote;
  if (!quote || typeof quote !== "object" || Array.isArray(quote))
    fail("标注必须包含 quote 对象");
  if (typeof quote.english !== "string" || !quote.english.trim())
    fail("quote.english 不能为空");
  if (typeof quote.chinese !== "string" || !quote.chinese.trim())
    fail("quote.chinese 不能为空");

  // 用 CLI 的 schema 校验文本长度、必需学习字段等。
  const schema = await cliFn(["schema"]);
  const schemas = schema?.schemas;
  if (!schemas?.label || !schemas?.quote)
    fail("无法从 CLI schema 获取标签/配文格式");
  const schemaProblems = [];
  labels.forEach((label, index) =>
    schemaProblems.push(
      ...schemaErrors(label, schemas.label, `labels[${index}]`),
    ),
  );
  schemaProblems.push(...schemaErrors(quote, schemas.quote, "quote"));
  if (schemaProblems.length) fail(`标注不符合 CLI schema：${schemaProblems.join("；")}`);

  const annotationsSHA256 = sha256(Buffer.from(annotationsText, "utf8"));
  const importFilename = `${job.cardID}-${imageSHA256.slice(0, 16)}${ext}`;

  const patch = {
    filename:
      typeof annotations.filename === "string" && annotations.filename.trim()
        ? annotations.filename
        : importFilename,
    labels,
    quote,
    rights: typeof annotations.rights === "string" ? annotations.rights : "",
    sourceURL:
      typeof annotations.sourceURL === "string" ? annotations.sourceURL : "",
  };

  return {
    imagePath: resolved.imagePath,
    imageSHA256,
    annotationsSHA256,
    annotationsText,
    importFilename,
    patch,
  };
}

// ---------------------------------------------------------------------------
// 比较：只比较 patch 提供的字段，兼容服务端补的默认字段。
// ---------------------------------------------------------------------------
function providedEqual(remote, provided) {
  if (Array.isArray(provided)) {
    if (!Array.isArray(remote) || remote.length !== provided.length)
      return false;
    return provided.every((item, index) => providedEqual(remote[index], item));
  }
  if (provided && typeof provided === "object") {
    if (!remote || typeof remote !== "object" || Array.isArray(remote))
      return false;
    return Object.keys(provided).every((key) =>
      providedEqual(remote[key], provided[key]),
    );
  }
  return remote === provided;
}

function matchesPatch(photo, patch) {
  if (!photo) return false;
  return Object.keys(patch).every((key) =>
    providedEqual(photo[key], patch[key]),
  );
}

function targetChanged(before, after, patch) {
  // labels 整体替换，连未显式提供的颜色等字段也不能覆盖他人的修改。
  return before?.assetID !== after?.assetID || Object.keys(patch).some(
    (key) => !isDeepStrictEqual(before?.[key], after?.[key]),
  );
}

// ---------------------------------------------------------------------------
// 回执与锁
// ---------------------------------------------------------------------------
async function readReceipt(receiptPath) {
  let text;
  try {
    text = await readFile(receiptPath, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
  try {
    return JSON.parse(text);
  } catch {
    fail("已有回执不是有效 JSON");
  }
}

async function writeReceipt(receiptPath, data) {
  const dir = path.dirname(receiptPath);
  await mkdir(dir, { recursive: true });
  const tmp = path.join(
    dir,
    `.${path.basename(receiptPath)}.${process.pid}.${randomBytes(6).toString("hex")}.tmp`,
  );
  await writeFile(tmp, `${JSON.stringify(data, null, 2)}\n`);
  await rename(tmp, receiptPath);
}

async function withLock(receiptPath, fn) {
  await mkdir(path.dirname(receiptPath), { recursive: true });
  const lockPath = `${receiptPath}.lock`;
  try {
    await mkdir(lockPath);
  } catch (error) {
    if (error.code === "EEXIST")
      fail("已有导入任务在进行中（receipt.lock 已存在），拒绝并发执行");
    throw error;
  }
  try {
    return await fn();
  } finally {
    await rm(lockPath, { recursive: true, force: true });
  }
}

function validateReceipt(receipt, job) {
  if (!receipt || typeof receipt !== "object") return;
  if (receipt.cardID && receipt.cardID !== job.cardID)
    fail("回执 cardID 与 job 不匹配");
  if (receipt.deckID && receipt.deckID !== job.deckID)
    fail("回执 deckID 与 job 不匹配");
  if (
    receipt.imageSHA256 &&
    receipt.imageSHA256.toLowerCase() !== job.imageSHA256.toLowerCase()
  )
    fail("回执 imageSHA256 与 job 不匹配");
}

// ---------------------------------------------------------------------------
// runCLI 适配
// ---------------------------------------------------------------------------
function makeRunner(cliFn) {
  return (args, json) =>
    cliFn(args, {
      stdin: Readable.from(json === undefined ? [] : [JSON.stringify(json)]),
    });
}

function findCardsById(deck, id) {
  return (deck?.draft?.cards ?? []).find((card) => card.id === id) ?? null;
}

function findCardsByFilename(deck, filename) {
  return (deck?.draft?.cards ?? []).filter(
    (card) => card.filename === filename,
  );
}

// 上传：一次 decks get + 一次 photos add；连接中断/冲突按规则恢复或停止。
async function uploadOnce({ run, deckID, revision, file, photoCount }) {
  const result = await run([
    "photos",
    "add",
    "--deck",
    deckID,
    "--revision",
    String(revision),
    file,
  ]);
  const photo = result?.photos?.[0];
  if (!photo) fail("上传响应缺少照片");
  return { photo, revision: result.revision, photoCount: photoCount + 1 };
}

async function recoverByFilename({ run, deckID, filename }) {
  const deck = await run(["decks", "get", "--deck", deckID]);
  const matches = findCardsByFilename(deck, filename);
  if (matches.length > 1)
    fail(`卡组中存在 ${matches.length} 张同名导入照片（${filename}），拒绝继续`);
  if (matches.length === 1)
    return { photo: matches[0], revision: deck.revision, photoCount: deck.draft.cards.length };
  return null;
}

async function uploadWithRecovery({ run, deckID, revision, file, filename, photoCount }) {
  try {
    return await uploadOnce({ run, deckID, revision, file, photoCount });
  } catch (error) {
    if (error?.code === "connection_failed") {
      const found = await recoverByFilename({ run, deckID, filename });
      if (found) return found;
      fail("上传连接中断且未找到已上传照片，已保留回执并停止（不盲目重传）");
    }
    if (error?.code === "revision_conflict") {
      const deck = await run(["decks", "get", "--deck", deckID]);
      const matches = findCardsByFilename(deck, filename);
      if (matches.length > 1)
        fail(
          `卡组中存在 ${matches.length} 张同名导入照片（${filename}），拒绝继续`,
        );
      if (matches.length === 1)
        return { photo: matches[0], revision: deck.revision, photoCount: deck.draft.cards.length };
      try {
        return await uploadOnce({
          run,
          deckID,
          revision: deck.revision,
          file,
          photoCount: deck.draft.cards.length,
        });
      } catch (retryError) {
        if (retryError?.code === "connection_failed") {
          const retried = await recoverByFilename({
            run,
            deckID,
            filename,
          });
          if (retried) return retried;
          fail("上传重试连接中断且未找到照片，已保留回执并停止");
        }
        throw retryError;
      }
    }
    throw error;
  }
}

// 更新：内容已一致则跳过；409 只有在目标照片未被他人修改时重试一次；
// 连接中断则读取远端内容，已一致视为成功，否则停止且不重试。
async function updateWithRecovery({
  run,
  deckID,
  photoID,
  revision,
  patch,
  lastSeen,
}) {
  try {
    return await updateOnce({ run, deckID, photoID, revision, patch });
  } catch (error) {
    if (error?.code === "connection_failed") {
      const current = await readTarget({ run, deckID, photoID });
      if (current && matchesPatch(current, patch))
        return { photo: current, revision: current.__revision, photoCount: current.__photoCount };
      fail("更新连接中断且远端内容与标注不一致，已停止（不重试）");
    }
    if (error?.code === "revision_conflict") {
      const current = await readTarget({ run, deckID, photoID });
      if (!current) fail("目标照片已不存在于卡组中");
      if (targetChanged(lastSeen, current, patch))
        fail("目标照片已被他人修改，拒绝覆盖");
      try {
        const result = await updateOnce({
          run,
          deckID,
          photoID,
          revision: current.__revision,
          patch,
        });
        return { ...result, photoCount: current.__photoCount };
      } catch (retryError) {
        if (retryError?.code === "connection_failed") {
          const after = await readTarget({ run, deckID, photoID });
          if (after && matchesPatch(after, patch))
            return { photo: after, revision: after.__revision, photoCount: after.__photoCount };
          fail("更新重试连接中断且远端内容不一致，已停止");
        }
        throw retryError;
      }
    }
    throw error;
  }
}

async function updateOnce({ run, deckID, photoID, revision, patch }) {
  const result = await run(
    [
      "photos",
      "update",
      "--deck",
      deckID,
      "--photo",
      photoID,
      "--revision",
      String(revision),
      "--file",
      "-",
    ],
    patch,
  );
  if (!result?.photo) fail("更新响应缺少照片");
  return { photo: result.photo, revision: result.revision };
}

async function readTarget({ run, deckID, photoID }) {
  const deck = await run(["decks", "get", "--deck", deckID]);
  const card = findCardsById(deck, photoID);
  if (!card) return null;
  card.__revision = deck.revision;
  card.__photoCount = deck.draft.cards.length;
  return card;
}

// ---------------------------------------------------------------------------
// 主流程
// ---------------------------------------------------------------------------
async function execute({ job, resolved, loaded, run }) {
  const timings = {};
  const timed = async (name, fn) => {
    const start = now();
    try {
      return await fn();
    } finally {
      timings[name] = (timings[name] ?? 0) + (now() - start);
    }
  };

  const base = {
    cardID: job.cardID,
    deckID: job.deckID,
    imageSHA256: loaded.imageSHA256,
    annotationsSHA256: loaded.annotationsSHA256,
    importFilename: loaded.importFilename,
  };
  const state = {
    status: "pending",
    photoID: null,
    assetID: null,
    revision: null,
  };
  const persist = (extra = {}) =>
    writeReceipt(resolved.receiptPath, {
      ...base,
      ...state,
      ...extra,
      updatedAt: new Date().toISOString(),
    });

  let receipt = await readReceipt(resolved.receiptPath);
  validateReceipt(receipt, job);
  if (receipt?.photoID) state.photoID = receipt.photoID;
  if (receipt?.assetID) state.assetID = receipt.assetID;
  if (receipt?.revision) state.revision = receipt.revision;

  let tempDir = null;
  try {
    if (job.photoID && receipt?.photoID && job.photoID !== receipt.photoID)
      fail("job.photoID 与回执 photoID 不一致");

    const deck = await timed("read", () =>
      run(["decks", "get", "--deck", job.deckID]),
    );

    let photo = null;
    let photoCount = deck.draft.cards.length;
    const knownID = job.photoID ?? receipt?.photoID ?? null;
    if (knownID) {
      photo = findCardsById(deck, knownID);
      if (!photo) fail("指定的 photoID 确实不属于该卡组");
    } else {
      const matches = findCardsByFilename(deck, loaded.importFilename);
      if (matches.length > 1)
        fail(
          `卡组中存在 ${matches.length} 张同名导入照片（${loaded.importFilename}），拒绝继续`,
        );
      if (matches.length === 1) photo = matches[0];
    }
    if (job.expectedAssetID) {
      if (!photo) fail("job.expectedAssetID 已提供但卡组中未找到对应照片");
      if (photo.assetID !== job.expectedAssetID)
        fail("expectedAssetID 与卡组照片不一致");
    }
    if (photo) {
      if (receipt?.assetID && receipt.assetID !== photo.assetID)
        fail("回执 assetID 与当前照片不一致，拒绝把旧标注套在新图上");
      state.photoID = photo.id;
      state.assetID = photo.assetID;
      state.revision = deck.revision;
    }

    if (!photo) {
      state.status = "uploading";
      await persist({ status: "uploading" });
      tempDir = await mkdtemp(path.join(os.tmpdir(), "piclex-import-"));
      const uploadFile = path.join(tempDir, loaded.importFilename);
      await copyFile(loaded.imagePath, uploadFile);
      const result = await timed("upload", () =>
        uploadWithRecovery({
          run,
          deckID: job.deckID,
          revision: deck.revision,
          file: uploadFile,
          filename: loaded.importFilename,
          photoCount,
        }),
      );
      photo = result.photo;
      photoCount = result.photoCount;
      state.photoID = photo.id;
      state.assetID = photo.assetID;
      state.revision = result.revision;
      state.status = "uploaded";
      await persist({ status: "uploaded", revision: state.revision });
    }

    if (!matchesPatch(photo, loaded.patch)) {
      const result = await timed("update", () =>
        updateWithRecovery({
          run,
          deckID: job.deckID,
          photoID: state.photoID,
          revision: state.revision,
          patch: loaded.patch,
          lastSeen: photo,
        }),
      );
      photo = result.photo;
      photoCount = result.photoCount ?? photoCount;
      state.revision = result.revision;
      state.status = "updated";
      await persist({ status: "updated", revision: state.revision });
    }

    if (!matchesPatch(photo, loaded.patch))
      fail("导入后照片内容与标注不一致");

    const checked = await timed("check", () =>
      run(["check", "--deck", job.deckID]),
    );
    if (!Array.isArray(checked?.errors)) fail("check 响应缺少 errors 数组，无法确认校验成功");
    const errors = checked.errors;
    if (errors.length) {
      state.status = "check_failed";
      await persist({ status: "check_failed", checked: errors });
      fail(`check 未通过：${errors.join("；")}`);
    }

    const summary = {
      status: "done",
      cardID: job.cardID,
      deckID: job.deckID,
      photoID: state.photoID,
      assetID: state.assetID,
      revision: state.revision,
      imageSHA256: loaded.imageSHA256,
      annotationsSHA256: loaded.annotationsSHA256,
      importFilename: loaded.importFilename,
      checked: errors,
      photoCount,
      timings: { ...timings, total: Object.values(timings).reduce((a, b) => a + b, 0) },
    };
    state.status = "done";
    await persist({
      status: "done",
      photoID: state.photoID,
      assetID: state.assetID,
      revision: state.revision,
      checked: errors,
      photoCount,
      timings: summary.timings,
    });
    return summary;
  } catch (error) {
    if (state.status !== "check_failed") {
      try {
        await persist({
          status: "failed",
          error: String(error?.message ?? error).slice(0, MAX_TEXT_SAMPLE),
        });
      } catch {
        // 回执写入失败不能掩盖原始错误。
      }
    }
    throw error;
  } finally {
    if (tempDir) await rm(tempDir, { recursive: true, force: true });
  }
}

async function loadCLI(cliPath) {
  try {
    const mod = await import(pathToFileURL(cliPath).href);
    if (typeof mod.runCLI !== "function")
      fail(`CLI 模块没有导出 runCLI：${cliPath}`);
    return mod.runCLI;
  } catch (error) {
    if (error instanceof ImportError) throw error;
    fail(`无法加载 CLI：${cliPath}（${error.message}）`);
  }
}

export async function runImport(jobPath, { dryRun = false, cli } = {}) {
  if (typeof jobPath !== "string" || !jobPath)
    fail("缺少 job 路径");
  const jobDir = path.dirname(path.resolve(jobPath));
  let job;
  try {
    job = JSON.parse(await readFile(path.resolve(jobPath), "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") fail(`job 文件不存在：${jobPath}`);
    if (error instanceof SyntaxError) fail("job 文件不是有效 JSON");
    throw error;
  }
  validateJobShape(job);
  const resolved = resolveJob(job, jobDir);
  const cliFn = typeof cli === "function" ? cli : await loadCLI(cli ?? DEFAULT_CLI);
  const run = makeRunner(cliFn);

  const loaded = await loadAndValidate(job, resolved, cliFn);

  if (dryRun) {
    return {
      dryRun: true,
      cardID: job.cardID,
      deckID: job.deckID,
      imagePath: loaded.imagePath,
      imageSHA256: loaded.imageSHA256,
      annotationsPath: resolved.annotationsPath,
      annotationsSHA256: loaded.annotationsSHA256,
      expectedWords: job.expectedWords,
      importFilename: loaded.importFilename,
      receiptPath: resolved.receiptPath,
      plan: [
        "读取卡组最新 revision",
        `若卡组中没有 ${loaded.importFilename} 则单张上传`,
        "若远端照片字段与标注不一致则一次 photos update 写入完整标注",
        "check --deck 校验并输出回执",
      ],
    };
  }

  return withLock(resolved.receiptPath, () =>
    execute({ job, resolved, loaded, run }),
  );
}

const HELP = `单图 PicLex 快速导入器

  node import-piclex.mjs --job manifest.json [--dry-run] [--cli path]

  --job       导入 job（JSON）
  --dry-run   只做本地校验并输出计划，不访问服务、不建锁、不建临时图
  --cli       官方 workbench CLI 绝对路径（默认 ${DEFAULT_CLI}）
`;

export async function main(argv = process.argv.slice(2)) {
  let values;
  try {
    ({ values } = parseArgs({
      args: argv,
      options: {
        job: { type: "string" },
        "dry-run": { type: "boolean" },
        cli: { type: "string" },
        help: { type: "boolean" },
      },
      strict: true,
    }));
  } catch {
    process.stderr.write(
      `${JSON.stringify({ ok: false, error: { code: "invalid_arguments", message: "参数不正确" } })}\n`,
    );
    process.exitCode = 1;
    return;
  }
  if (values.help || !values.job) {
    process.stdout.write(HELP);
    return;
  }
  try {
    const result = await runImport(values.job, {
      dryRun: !!values["dry-run"],
      cli: values.cli,
    });
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    process.stderr.write(
      `${JSON.stringify({
        ok: false,
        error: {
          code: error instanceof ImportError ? "import_failed" : "unexpected",
          message: String(error?.message ?? error),
        },
      })}\n`,
    );
    process.exitCode = 1;
  }
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
)
  await main();
