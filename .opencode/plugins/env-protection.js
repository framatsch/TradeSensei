/**
 * env-protection.js
 *
 * OpenCode plugin — blocks agents from reading .env files.
 *
 * Intercepts any file-read tool call where the path matches a .env pattern
 * and rejects it with an explanatory message before the content is exposed.
 */

export default {
  name: "env-protection",
  description: "Blocks agents from reading .env files to prevent secret leakage",

  /**
   * Hook: beforeToolCall
   *
   * Called before every tool invocation. If the tool is a file-read operation
   * targeting a .env file, the call is cancelled and a warning is returned.
   *
   * @param {object} tool  - The tool being called ({ name, input })
   * @returns {object|undefined} - Return an object with `cancel: true` and a
   *   `message` to block the call, or return undefined to allow it through.
   */
  beforeToolCall(tool) {
    const readTools = ["Read", "read_file", "view_file"];

    if (!readTools.includes(tool.name)) {
      return undefined;
    }

    const filePath = tool.input?.filePath ?? tool.input?.path ?? "";

    // Match .env, .env.local, .env.production, .env.test, etc.
    const envPattern = /(^|[\\/])\.env(\.[^/\\]*)?$/;

    if (envPattern.test(filePath)) {
      return {
        cancel: true,
        message:
          `[env-protection] Blocked attempt to read "${filePath}". ` +
          ".env files may contain secrets and must not be read by agents. " +
          "Use environment variable references (process.env.VAR) instead.",
      };
    }

    return undefined;
  },
};
