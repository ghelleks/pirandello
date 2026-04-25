import * as os from "node:os";
import * as path from "node:path";

/** Canonical clone URL for the Pirandello framework (override via fork settings later). */
export const PIRANDELLO_REPO_URL = "https://github.com/example/pirandello.git";

export function pirandelloHome(): string {
  const base = process.env.PIRANDELLO_HOME?.trim();
  if (base) return path.resolve(base);
  return path.join(os.homedir(), "Code", "pirandello");
}
