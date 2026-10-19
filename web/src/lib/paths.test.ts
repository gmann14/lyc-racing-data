import { test } from "node:test";
import assert from "node:assert/strict";
import { isActivePath, normalizePath } from "./paths.ts";

test("normalizePath strips trailing slashes", () => {
  assert.equal(normalizePath("/boats/"), "/boats");
  assert.equal(normalizePath("/boats"), "/boats");
  assert.equal(normalizePath("/"), "/");
  assert.equal(normalizePath(""), "/");
});

test("isActivePath matches basePath-free pathnames with or without trailing slash", () => {
  assert.equal(isActivePath("/boats", "/boats/"), true);
  assert.equal(isActivePath("/boats/", "/boats/"), true);
  assert.equal(isActivePath("/trophies/some-trophy", "/trophies/"), true);
});

test("isActivePath only marks Home on the root page", () => {
  assert.equal(isActivePath("/", "/"), true);
  assert.equal(isActivePath("/boats/", "/"), false);
});

test("isActivePath rejects prefixes, basePath-prefixed paths and null", () => {
  assert.equal(isActivePath("/boatsx", "/boats/"), false);
  assert.equal(isActivePath("/lyc-racing-data/boats/", "/boats/"), false);
  assert.equal(isActivePath(null, "/"), false);
});
