import { spawn } from "child_process";
import { writeFileSync } from "fs";

await new Promise((resolve) => {
  const p = spawn(
    "./node_modules/.bin/playwright",
    ["test", "tests/auth.spec.ts:40", "--reporter=line"],
    { cwd: process.cwd(), shell: false }
  );
  let out = "";
  let err = "";
  p.stdout.on("data", (d) => (out += d.toString()));
  p.stderr.on("data", (d) => (err += d.toString()));
  p.on("close", (code) => {
    writeFileSync("spawn-out.txt", `code=${code}\n---stdout---\n${out}\n---stderr---\n${err}`);
    resolve();
  });
});
