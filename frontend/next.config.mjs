import { execSync } from "child_process";

/** @type {import('next').NextConfig} */

// Resolve the current version from the nearest git tag at build time.
// Falls back to the version in package.json if git is unavailable.
function resolveAppVersion() {
  try {
    const tag = execSync("git describe --tags --abbrev=0 2>/dev/null", { encoding: "utf8" }).trim();
    // Strip leading "v" if present (v0.3.0 → 0.3.0)
    return tag.replace(/^v/, "");
  } catch {
    // git not available (e.g. in a Docker layer without .git)
    const pkg = JSON.parse(
      execSync("cat ../package.json 2>/dev/null || cat package.json", {
        encoding: "utf8",
        cwd: new URL(".", import.meta.url).pathname,
      })
    );
    return pkg.version ?? "0.0.0";
  }
}

const appVersion = resolveAppVersion();

const nextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_APP_VERSION: appVersion,
  },
};

export default nextConfig;
