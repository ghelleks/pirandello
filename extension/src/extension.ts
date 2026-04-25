import * as crypto from "node:crypto";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import * as vscode from "vscode";
import { PIRANDELLO_REPO_URL, pirandelloHome } from "./config";

const OUTPUT = vscode.window.createOutputChannel("Pirandello");

function log(msg: string) {
  OUTPUT.appendLine(msg);
}

function sh256(s: string) {
  return crypto.createHash("sha256").update(s).digest("hex");
}

function masksBase(): string {
  const b = process.env.MASKS_BASE?.trim();
  if (b) return path.resolve(b);
  return path.join(os.homedir(), "Desktop");
}

function isRoleWorkspace(root: string): boolean {
  const roleMd = path.join(root, "ROLE.md");
  const git = path.join(root, ".git");
  const parent = path.dirname(root);
  if (!fs.existsSync(roleMd) || !fs.existsSync(git)) return false;
  return path.resolve(parent) === path.resolve(masksBase());
}

function ensureUv(): boolean {
  const r = spawnSync("uv", ["--version"], { encoding: "utf-8" });
  if (r.error || r.status !== 0) {
    void vscode.window.showErrorMessage(
      "Pirandello needs the `uv` Python tool installer. Install it from the official Astral guide, then reload Cursor.",
      "Open install instructions"
    ).then((c) => {
      if (c) void vscode.env.openExternal(vscode.Uri.parse("https://docs.astral.sh/uv/getting-started/installation/"));
    });
    return false;
  }
  return true;
}

function ensureRepo(): boolean {
  const dest = pirandelloHome();
  const marker = path.join(dest, "cli", "pyproject.toml");
  if (fs.existsSync(marker)) return true;
  const r = spawnSync("git", ["clone", "--depth", "1", PIRANDELLO_REPO_URL, dest], { encoding: "utf-8" });
  if (r.status !== 0) {
    log(`git clone failed: ${r.stderr || r.stdout}`);
    void vscode.window.showErrorMessage("Pirandello: could not clone framework repository.");
    return false;
  }
  return true;
}

function ensureMasksCli(): boolean {
  const r = spawnSync("masks", ["--version"], { encoding: "utf-8" });
  if (r.status === 0) return true;
  const home = pirandelloHome();
  const cli = path.join(home, "cli");
  const ins = spawnSync("uv", ["tool", "install", cli], { encoding: "utf-8" });
  if (ins.status !== 0) {
    log(ins.stderr || ins.stdout || "uv tool install failed");
    void vscode.window.showErrorMessage("Pirandello: could not install masks CLI.");
    return false;
  }
  return true;
}

async function ensureSetup(ctx: vscode.ExtensionContext) {
  if (ctx.globalState.get("pirandello.bootstrap.setupComplete")) return;
  const base = masksBase();
  const personalRole = path.join(base, "personal", "ROLE.md");
  const agents = path.join(base, "AGENTS.md");
  if (fs.existsSync(personalRole) && fs.existsSync(agents)) {
    await ctx.globalState.update("pirandello.bootstrap.setupComplete", true);
    await ctx.globalState.update("pirandello.bootstrap.masksBase", base);
    return;
  }
  const r = spawnSync("masks", ["setup"], { cwd: os.homedir(), encoding: "utf-8" });
  if (r.status !== 0) {
    log(r.stderr || r.stdout || "masks setup failed");
    return;
  }
  await ctx.globalState.update("pirandello.bootstrap.setupComplete", true);
  await ctx.globalState.update("pirandello.bootstrap.masksBase", base);
}

async function maybeOnboarding(ctx: vscode.ExtensionContext) {
  if (ctx.globalState.get("pirandello.bootstrap.onboardingComplete")) return;
  const base = (ctx.globalState.get("pirandello.bootstrap.masksBase") as string) || masksBase();
  const self = path.join(base, "personal", "SELF.md");
  if (fs.existsSync(self) && fs.statSync(self).size > 200) {
    await ctx.globalState.update("pirandello.bootstrap.onboardingComplete", true);
    return;
  }
  const seed =
    "You are helping me finish Pirandello onboarding. Open and follow the onboarding skill at " +
    "`skills/mask-onboarding/SKILL.md` in the Pirandello repo (already on this machine). Start at Phase 1 — Identity. " +
    "Ask me questions one at a time; write files only as that skill specifies. Do not skip phases.";
  await vscode.env.clipboard.writeText(seed);
  void vscode.window.showInformationMessage(
    "Your Pirandello setup message is copied. Open Agent chat and paste to begin."
  );
  await vscode.commands.executeCommand("workbench.action.chat.open");
}

function wrapperStart(home: string): string {
  return `#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null || true
cd "\${CURSOR_PROJECT_DIR:-.}" || exit 0
PIRANDELLO_HOME="\${PIRANDELLO_HOME:-${home}}"
OUT="$(bash "$PIRANDELLO_HOME/hooks/start.sh" 2>/dev/null || true)"
python3 -c 'import json,sys; print(json.dumps({"additional_context": sys.argv[1]}))' "$OUT" || echo '{"additional_context":""}'
`;
}

function wrapperEnd(home: string): string {
  return `#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null || true
cd "\${CURSOR_PROJECT_DIR:-.}" || exit 0
PIRANDELLO_HOME="\${PIRANDELLO_HOME:-${home}}"
bash "$PIRANDELLO_HOME/hooks/end.sh" 2>/dev/null || true
echo '{}'
`;
}

function writeHooksIfNeeded(roleRoot: string) {
  const home = pirandelloHome();
  const cursor = path.join(roleRoot, ".cursor");
  const hooksDir = path.join(cursor, "hooks");
  fs.mkdirSync(hooksDir, { recursive: true });
  const startPath = path.join(hooksDir, "pirandello-session-start.sh");
  const endPath = path.join(hooksDir, "pirandello-session-end.sh");
  const startBody = wrapperStart(home);
  const endBody = wrapperEnd(home);
  const hooksJson = {
    version: 1,
    hooks: {
      sessionStart: [{ command: ".cursor/hooks/pirandello-session-start.sh", timeout: 120 }],
      sessionEnd: [{ command: ".cursor/hooks/pirandello-session-end.sh", timeout: 120 }],
    },
  };
  const jpath = path.join(cursor, "hooks.json");
  const desired = JSON.stringify(hooksJson, null, 2) + "\n";
  const writeIfChanged = (p: string, body: string) => {
    if (fs.existsSync(p) && fs.readFileSync(p, "utf8") === body) return;
    fs.writeFileSync(p, body, "utf8");
    fs.chmodSync(p, 0o755);
  };
  if (!fs.existsSync(jpath) || sh256(fs.readFileSync(jpath, "utf8")) !== sh256(desired)) {
    fs.writeFileSync(jpath, desired, "utf8");
  }
  writeIfChanged(startPath, startBody);
  writeIfChanged(endPath, endBody);
}

export async function activate(ctx: vscode.ExtensionContext) {
  if (!ensureUv()) return;
  if (!ensureRepo()) return;
  if (!ensureMasksCli()) return;
  await ensureSetup(ctx);
  await maybeOnboarding(ctx);

  const run = () => {
    const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!folder) return;
    if (!isRoleWorkspace(folder)) return;
    try {
      writeHooksIfNeeded(folder);
    } catch (e) {
      log(`hook write error: ${e}`);
    }
  };
  run();
  vscode.workspace.onDidChangeWorkspaceFolders(run);
  vscode.window.onDidChangeWindowState((s) => {
    if (s.focused) run();
  });
}

export function deactivate() {}
