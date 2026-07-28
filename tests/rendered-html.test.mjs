import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("ClipTime interface contains the complete local workflow", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(page, /СОЗДАТЬ КЛИПЫ/);
  assert.match(page, /http:\/\/127\.0\.0\.1:8765\/api/);
  assert.match(page, /clip_count/);
  assert.match(page, /download_url/);
  assert.match(css, /--accent: #4f46e5/);
  assert.match(css, /@media \(max-width: 560px\)/);
});
