const test = require("node:test");
const assert = require("node:assert/strict");
const parseDuration = require("../src/parseDuration");

test("all units", () => {
  assert.equal(parseDuration("1d2h3m4s"), 86400 + 7200 + 180 + 4);
});

test("whitespace and case", () => {
  assert.equal(parseDuration("2D 4H"), 2 * 86400 + 4 * 3600);
  assert.equal(parseDuration(" 1h  5M 3s "), 3600 + 300 + 3);
});

test("zero", () => {
  assert.equal(parseDuration("0s"), 0);
});

test("rejects bad input", () => {
  for (const bad of ["", "abc", "1x", "30m1h", "1h1h", "1.5h", "-1h", 42, null, "h"]) {
    assert.throws(() => parseDuration(bad), TypeError, `expected TypeError for ${String(bad)}`);
  }
});
