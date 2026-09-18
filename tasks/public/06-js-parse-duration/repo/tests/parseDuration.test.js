const test = require("node:test");
const assert = require("node:assert/strict");
const parseDuration = require("../src/parseDuration");

test("hours and minutes", () => {
  assert.equal(parseDuration("1h30m"), 5400);
});

test("seconds only", () => {
  assert.equal(parseDuration("45s"), 45);
});
