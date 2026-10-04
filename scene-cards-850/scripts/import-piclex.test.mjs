import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mkdtemp,
  mkdir,
  writeFile,
  readFile,
  rm,
  stat,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createHash, randomUUID } from "node:crypto";
import { runImport } from "./import-piclex.mjs";

const sha256 = (buffer) => createHash("sha256").update(buffer).digest("hex");
const CARD_ID = "11111111-1111-4111-8111-111111111111";
const DECK_ID = "22222222-2222-4222-8222-222222222222";
const PHOTO_ID = "33333333-3333-4333-8333-333333333333";
const ASSET_ID = "a".repeat(64);
const WORDS = [
  "bed",
  "sleep",
  "awake",
  "morning",
  "clock",
  "curtain",
  "light",
  "early",
  "be",
];

// 与 CLI schema 同形的测试 schema（含长度与必需字段约束）。
const FAKE_SCHEMA = {
  schemas: {
    label: {
      type: "object",
      required: ["x", "y", "english", "chinese"],
      properties: {
        x: { type: "integer", minimum: 0, maximum: 1000 },
        y: { type: "integer", minimum: 0, maximum: 1000 },
        english: { type: "string", maxLength: 120 },
        chinese: { type: "string", maxLength: 120 },
        phoneticUS: { type: "string", maxLength: 120 },
        phoneticUK: { type: "string", maxLength: 120 },
        learning: {
          anyOf: [
            {
              type: "object",
              required: [
                "partOfSpeech",
                "relation",
                "sceneConnection",
                "association",
                "collocation",
                "example",
                "exampleChinese",
              ],
              properties: {
                partOfSpeech: { type: "string", maxLength: 40 },
                relation: {
                  type: "string",
                  enum: ["visible", "scene_extension", "hypothetical"],
                },
                sceneConnection: { type: "string", maxLength: 400 },
                association: { type: "string", maxLength: 400 },
                collocation: { type: "string", maxLength: 160 },
                example: { type: "string", maxLength: 500 },
                exampleChinese: { type: "string", maxLength: 500 },
              },
            },
            { type: "null" },
          ],
        },
      },
    },
    quote: {
      type: "object",
      required: ["english", "chinese", "source"],
      properties: {
        english: { type: "string", maxLength: 2000 },
        chinese: { type: "string", maxLength: 2000 },
        source: { type: "string", maxLength: 300 },
        sourceURL: {
          anyOf: [
            { type: "string", const: "" },
            { type: "string", format: "uri" },
          ],
        },
        provenance: {
          type: "string",
          enum: ["web", "model", "none"],
        },
      },
    },
  },
};

function makeLabel(english, index) {
  const visible = index < 2;
  const x = 100 + index * 40;
  const y = 100 + index * 40;
  return {
    x,
    y,
    english,
    chinese: `释义${index}`,
    phoneticUS: "/x/",
    phoneticUK: "/x/",
    bubblePosition: { x: 10 + index, y: 20 + index },
    anchorPosition: visible ? { x, y } : null,
    boundingBox: visible
      ? { left: 40, top: 40, right: 400, bottom: 400 }
      : null,
    positionUnavailable: !visible,
    learning: {
      partOfSpeech: "noun",
      relation: visible ? "visible" : "scene_extension",
      sceneConnection: "画面证据",
      association: "联想",
      collocation: "搭配",
      example: "Example sentence.",
      exampleChinese: "例句。",
    },
  };
}

function makeAnnotations(words = WORDS) {
  return {
    filename: "C001-清晨醒来.png",
    labels: words.map(makeLabel),
    quote: {
      english: "I am awake, and the morning light is on my bed.",
      chinese: "我醒了，晨光照在我的床上。",
      source: "原创配文",
      sourceURL: "",
      provenance: "model",
    },
    rights: "本项目用内置 image_gen 生成的图片；配文为原创。",
    sourceURL: "",
  };
}

async function fixture(t, options = {}) {
  const root = await mkdtemp(path.join(tmpdir(), "piclex-import-test-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const annotations = options.annotations ?? makeAnnotations();
  const imageName = "C001-清晨醒来.png";
  const imageBytes = Buffer.from(`fake-image-${randomUUID()}`);
  await writeFile(path.join(root, imageName), imageBytes);
  await writeFile(
    path.join(root, "annotations.json"),
    JSON.stringify(annotations),
  );
  const job = {
    cardID: CARD_ID,
    imagePath: imageName,
    imageSHA256: sha256(imageBytes),
    imageReviewed: true,
    annotationsPath: "annotations.json",
    deckID: DECK_ID,
    expectedWords: annotations.labels.map((label) => label.english),
    receiptPath: "receipt.json",
    ...(options.job ?? {}),
  };
  const jobPath = path.join(root, "job.json");
  await writeFile(jobPath, JSON.stringify(job));
  return {
    root,
    jobPath,
    job,
    annotations,
    imageBytes,
    receiptPath: path.join(root, "receipt.json"),
    async writeJob(patch) {
      Object.assign(job, patch);
      await writeFile(jobPath, JSON.stringify(job));
    },
  };
}

function cliError(code, message = code) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function parseFake(args) {
  const values = {};
  const positionals = [];
  for (let i = 0; i < args.length; i += 1) {
    if (args[i].startsWith("--")) {
      values[args[i].slice(2)] = args[i + 1];
      i += 1;
    } else positionals.push(args[i]);
  }
  return { values, positionals };
}

async function readJSONStdin(stdin) {
  const chunks = [];
  for await (const chunk of stdin) chunks.push(Buffer.from(chunk));
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function fakeCLI(options = {}) {
  const state = {
    revision: 1,
    cards: [],
    calls: [],
    deckGetCount: 0,
    photosAddCount: 0,
    photosUpdateCount: 0,
    checkCount: 0,
  };
  const defaultAdd = async ({ file }) => {
    const card = {
      id: randomUUID(),
      assetID: sha256(await readFile(file)),
      createdAt: Date.now(),
      filename: path.basename(file),
      filenameEncoding: "utf-8",
      labels: [],
      quote: {
        english: "",
        chinese: "",
        source: "",
        sourceURL: "",
        provenance: "none",
      },
      rights: "",
      sourceURL: "",
    };
    state.cards.push(card);
    state.revision += 1;
    return {
      deckID: DECK_ID,
      revision: state.revision,
      photos: [structuredClone(card)],
    };
  };
  const defaultUpdate = async ({ values, stdin }) => {
    const card = state.cards.find((item) => item.id === values.photo);
    if (!card) throw cliError("photo_not_found");
    if (Number(values.revision) !== state.revision)
      throw cliError("revision_conflict");
    const patch = await readJSONStdin(stdin);
    if (patch.filename !== undefined) card.filename = patch.filename;
    if (patch.labels !== undefined)
      card.labels = patch.labels.map((label) => ({
        phoneticUS: "",
        phoneticUK: "",
        ...label,
        backgroundColor: label.backgroundColor ?? "#FFF5D6",
        textColor: label.textColor ?? "#292720",
      }));
    if (patch.quote !== undefined)
      card.quote = {
        sourceURL: "",
        provenance: "none",
        ...card.quote,
        ...patch.quote,
      };
    if (patch.rights !== undefined) card.rights = patch.rights;
    if (patch.sourceURL !== undefined) card.sourceURL = patch.sourceURL;
    state.revision += 1;
    return {
      deckID: DECK_ID,
      revision: state.revision,
      photo: structuredClone(card),
    };
  };
  const cli = async (args, { stdin } = {}) => {
    state.calls.push(args);
    const { values, positionals } = parseFake(args);
    const command = positionals.slice(0, 2).join(" ").trim();
    if (command === "schema") return FAKE_SCHEMA;
    if (command === "decks get") {
      state.deckGetCount += 1;
      return structuredClone({
        id: DECK_ID,
        revision: state.revision,
        draft: { cards: state.cards },
      });
    }
    if (command === "photos add") {
      state.photosAddCount += 1;
      if (options.onAdd)
        return options.onAdd({
          values,
          positionals,
          state,
          defaultAdd,
        });
      return defaultAdd({ file: positionals[2] });
    }
    if (command === "photos update") {
      state.photosUpdateCount += 1;
      if (options.onUpdate)
        return options.onUpdate({
          values,
          positionals,
          stdin,
          state,
          defaultUpdate,
        });
      return defaultUpdate({ values, stdin });
    }
    if (command === "check") {
      state.checkCount += 1;
      return { errors: (options.checkErrors ?? []).slice() };
    }
    throw new Error(`fake CLI 未实现：${args.join(" ")}`);
  };
  return { cli, state, defaultAdd, defaultUpdate };
}

function seedPhoto(fake, overrides = {}) {
  const card = {
    id: PHOTO_ID,
    assetID: ASSET_ID,
    createdAt: 1,
    filename: "旧图.png",
    filenameEncoding: "utf-8",
    labels: [],
    quote: {
      english: "old",
      chinese: "旧",
      source: "",
      sourceURL: "",
      provenance: "none",
    },
    rights: "旧",
    sourceURL: "",
    ...overrides,
  };
  fake.state.cards.push(card);
  fake.state.revision = 5;
  return card;
}

test("dry-run 只做本地校验，不访问服务也不建锁/回执", async (t) => {
  const f = await fixture(t);
  const fake = fakeCLI();
  const result = await runImport(f.jobPath, { dryRun: true, cli: fake.cli });
  assert.equal(result.dryRun, true);
  assert.equal(result.cardID, CARD_ID);
  assert.equal(
    result.importFilename,
    `${CARD_ID}-${f.job.imageSHA256.slice(0, 16)}.png`,
  );
  assert.equal(fake.state.photosAddCount, 0);
  assert.equal(fake.state.deckGetCount, 0);
  assert.equal(fake.state.checkCount, 0);
  assert.equal(
    fake.state.calls.filter((args) => args[0] !== "schema").length,
    0,
  );
  await assert.rejects(stat(f.receiptPath), { code: "ENOENT" });
  await assert.rejects(stat(`${f.receiptPath}.lock`), { code: "ENOENT" });
});

test("哈希、词集合、几何越界均在写前失败", async (t) => {
  const hashFixture = await fixture(t);
  await hashFixture.writeJob({ imageSHA256: "0".repeat(64) });
  const hashCli = fakeCLI();
  await assert.rejects(
    runImport(hashFixture.jobPath, { cli: hashCli.cli }),
    /SHA256/,
  );
  assert.equal(hashCli.state.calls.length, 0);

  const wordFixture = await fixture(t, {
    job: { expectedWords: WORDS.slice(0, 8) },
  });
  const wordCli = fakeCLI();
  await assert.rejects(
    runImport(wordFixture.jobPath, { cli: wordCli.cli }),
    /expectedWords/,
  );
  assert.equal(wordCli.state.calls.length, 0);

  const boxAnnotations = makeAnnotations();
  boxAnnotations.labels[0].boundingBox.right = 1001;
  const boxFixture = await fixture(t, { annotations: boxAnnotations });
  const boxCli = fakeCLI();
  await assert.rejects(
    runImport(boxFixture.jobPath, { cli: boxCli.cli }),
    /1000/,
  );
  assert.equal(boxCli.state.calls.length, 0);

  const anchorAnnotations = makeAnnotations();
  anchorAnnotations.labels[0].anchorPosition = { x: 999, y: 999 };
  const anchorFixture = await fixture(t, { annotations: anchorAnnotations });
  const anchorCli = fakeCLI();
  await assert.rejects(
    runImport(anchorFixture.jobPath, { cli: anchorCli.cli }),
    /指向点必须在框内/,
  );
  assert.equal(anchorCli.state.calls.length, 0);
});

test("schema 文本长度在写前失败", async (t) => {
  const annotations = makeAnnotations();
  annotations.labels[0].english = "a".repeat(130);
  const f = await fixture(t, { annotations });
  const fake = fakeCLI();
  await assert.rejects(
    runImport(f.jobPath, { cli: fake.cli }),
    /文本长度/,
  );
  assert.equal(fake.state.deckGetCount, 0);
  assert.equal(fake.state.photosAddCount, 0);
  assert.equal(fake.state.calls.length, 1);
  assert.deepEqual(fake.state.calls[0], ["schema"]);
});

test("首次运行上传一次并完整更新写入回执", async (t) => {
  const f = await fixture(t);
  const fake = fakeCLI();
  const result = await runImport(f.jobPath, { cli: fake.cli });
  assert.equal(fake.state.photosAddCount, 1);
  assert.equal(fake.state.photosUpdateCount, 1);
  assert.equal(fake.state.checkCount, 1);
  assert.equal(fake.state.deckGetCount, 1);
  assert.equal(result.status, "done");
  assert.equal(result.revision, 3);
  assert.equal(result.photoCount, 1);
  assert.deepEqual(result.checked, []);
  assert.deepEqual(
    fake.state.cards[0].labels.map((label) => label.english),
    WORDS,
  );
  assert.equal(
    fake.state.cards[0].quote.english,
    f.annotations.quote.english,
  );
  const receipt = JSON.parse(await readFile(f.receiptPath, "utf8"));
  assert.equal(receipt.status, "done");
  assert.equal(receipt.photoID, result.photoID);
  assert.equal(receipt.assetID, result.assetID);
  assert.equal(receipt.cardID, CARD_ID);
  assert.equal(receipt.deckID, DECK_ID);
  await assert.rejects(stat(`${f.receiptPath}.lock`), { code: "ENOENT" });
});

test("再次运行不重复上传、不改 revision", async (t) => {
  const f = await fixture(t);
  const fake = fakeCLI();
  const first = await runImport(f.jobPath, { cli: fake.cli });
  const second = await runImport(f.jobPath, { cli: fake.cli });
  assert.equal(fake.state.cards.length, 1);
  assert.equal(fake.state.photosAddCount, 1);
  assert.equal(fake.state.photosUpdateCount, 1);
  assert.equal(second.revision, first.revision);
  assert.equal(second.photoCount, 1);
});

test("上传实际成功但返回 connection_failed 后找回照片并继续", async (t) => {
  const f = await fixture(t);
  const fake = fakeCLI({
    onAdd: async ({ positionals, defaultAdd }) => {
      await defaultAdd({ file: positionals[2] });
      throw cliError("connection_failed", "连接中断");
    },
  });
  const result = await runImport(f.jobPath, { cli: fake.cli });
  assert.equal(fake.state.photosAddCount, 1);
  assert.equal(fake.state.cards.length, 1);
  assert.equal(result.status, "done");
  assert.equal(result.photoCount, 1);
  assert.equal(result.revision, 3);
});

test("更新连接中断但远端内容已一致视为成功", async (t) => {
  const f = await fixture(t);
  let injected = false;
  const fake = fakeCLI({
    onUpdate: async (ctx) => {
      if (!injected) {
        injected = true;
        await ctx.defaultUpdate({ values: ctx.values, stdin: ctx.stdin });
        throw cliError("connection_failed", "连接中断");
      }
      return ctx.defaultUpdate({ values: ctx.values, stdin: ctx.stdin });
    },
  });
  seedPhoto(fake);
  await f.writeJob({ photoID: PHOTO_ID, expectedAssetID: ASSET_ID });
  const result = await runImport(f.jobPath, { cli: fake.cli });
  assert.equal(result.status, "done");
  assert.equal(fake.state.photosUpdateCount, 1);
  assert.equal(result.revision, 6);
});

test("409 仅他人改动时可重试一次", async (t) => {
  const f = await fixture(t);
  let first = true;
  const fake = fakeCLI({
    onUpdate: async (ctx) => {
      if (first) {
        first = false;
        ctx.state.cards.push({
          id: randomUUID(),
          assetID: "b".repeat(64),
          createdAt: 2,
          filename: "other.png",
          labels: [],
          quote: {
            english: "",
            chinese: "",
            source: "",
            sourceURL: "",
            provenance: "none",
          },
          rights: "",
          sourceURL: "",
        });
        ctx.state.revision += 1;
        throw cliError("revision_conflict", "版本冲突");
      }
      return ctx.defaultUpdate({ values: ctx.values, stdin: ctx.stdin });
    },
  });
  seedPhoto(fake);
  await f.writeJob({ photoID: PHOTO_ID, expectedAssetID: ASSET_ID });
  const result = await runImport(f.jobPath, { cli: fake.cli });
  assert.equal(result.status, "done");
  assert.equal(fake.state.photosUpdateCount, 2);
  assert.equal(result.revision, 7);
  assert.equal(result.photoCount, 2);
});

test("409 连未在输入中提供的气泡颜色修改也不覆盖", async (t) => {
  const f = await fixture(t);
  const fake = fakeCLI({
    onUpdate: async (ctx) => {
      const card = ctx.state.cards.find((item) => item.id === PHOTO_ID);
      card.labels[0].backgroundColor = "#000000";
      ctx.state.revision += 1;
      throw cliError("revision_conflict");
    },
  });
  seedPhoto(fake, { labels: structuredClone(f.annotations.labels) });
  await f.writeJob({ photoID: PHOTO_ID, expectedAssetID: ASSET_ID });
  await assert.rejects(runImport(f.jobPath, { cli: fake.cli }), /拒绝覆盖/);
  assert.equal(fake.state.photosUpdateCount, 1);
  assert.equal(fake.state.cards[0].labels[0].backgroundColor, "#000000");
});

test("409 目标照片被他人修改时拒绝覆盖", async (t) => {
  const f = await fixture(t);
  let first = true;
  const fake = fakeCLI({
    onUpdate: async (ctx) => {
      if (first) {
        first = false;
        const card = ctx.state.cards.find((item) => item.id === PHOTO_ID);
        card.quote = { ...card.quote, english: "hijacked" };
        ctx.state.revision += 1;
        throw cliError("revision_conflict", "版本冲突");
      }
      return ctx.defaultUpdate({ values: ctx.values, stdin: ctx.stdin });
    },
  });
  seedPhoto(fake);
  await f.writeJob({ photoID: PHOTO_ID, expectedAssetID: ASSET_ID });
  await assert.rejects(
    runImport(f.jobPath, { cli: fake.cli }),
    /拒绝覆盖/,
  );
  assert.equal(fake.state.photosUpdateCount, 1);
  assert.equal(
    fake.state.cards.find((card) => card.id === PHOTO_ID).quote.english,
    "hijacked",
  );
});

test("既有 photoID 错误、asset 不符、回执不匹配均拒绝", async (t) => {
  const wrongFixture = await fixture(t);
  await wrongFixture.writeJob({ photoID: randomUUID() });
  const wrongCli = fakeCLI();
  await assert.rejects(
    runImport(wrongFixture.jobPath, { cli: wrongCli.cli }),
    /photoID/,
  );
  assert.equal(wrongCli.state.photosAddCount, 0);
  assert.equal(wrongCli.state.photosUpdateCount, 0);

  const assetFixture = await fixture(t);
  const assetCli = fakeCLI();
  seedPhoto(assetCli);
  await assetFixture.writeJob({
    photoID: PHOTO_ID,
    expectedAssetID: "c".repeat(64),
  });
  await assert.rejects(
    runImport(assetFixture.jobPath, { cli: assetCli.cli }),
    /expectedAssetID/,
  );
  assert.equal(assetCli.state.photosUpdateCount, 0);

  const receiptFixture = await fixture(t);
  await writeFile(
    receiptFixture.receiptPath,
    JSON.stringify({
      cardID: "99999999-9999-4999-8999-999999999999",
      deckID: DECK_ID,
      imageSHA256: receiptFixture.job.imageSHA256,
    }),
  );
  const receiptCli = fakeCLI();
  await assert.rejects(
    runImport(receiptFixture.jobPath, { cli: receiptCli.cli }),
    /回执 cardID/,
  );
  assert.equal(receiptCli.state.deckGetCount, 0);
  assert.equal(receiptCli.state.photosAddCount, 0);
});

test("check 失败时保留已上传/更新回执可续跑", async (t) => {
  const f = await fixture(t);
  const fake = fakeCLI({ checkErrors: ["第 1 张照片缺少版权／授权说明"] });
  await assert.rejects(
    runImport(f.jobPath, { cli: fake.cli }),
    /check 未通过/,
  );
  const receipt = JSON.parse(await readFile(f.receiptPath, "utf8"));
  assert.equal(receipt.status, "check_failed");
  assert.ok(receipt.photoID);
  assert.equal(receipt.revision, 3);
  assert.equal(fake.state.photosAddCount, 1);
});

test("已有锁时拒绝执行且不删除他人锁", async (t) => {
  const f = await fixture(t);
  const lockPath = `${f.receiptPath}.lock`;
  await mkdir(lockPath);
  const fake = fakeCLI();
  await assert.rejects(
    runImport(f.jobPath, { cli: fake.cli }),
    /receipt\.lock/,
  );
  assert.equal((await stat(lockPath)).isDirectory(), true);
  assert.equal(fake.state.deckGetCount, 0);
});
