#!/usr/bin/env node

const fs = require('fs');

try {
  const input = fs.readFileSync(0, 'utf-8');
  if (!input) {
    console.log(JSON.stringify({ decision: "allow" }));
    process.exit(0);
  }

  const data = JSON.parse(input);
  const readTools = ["Read", "read_file", "view_file"];
  const toolName = data.toolCall?.name;

  if (toolName && readTools.includes(toolName)) {
    const args = data.toolCall?.args || {};
    const filePath = args.filePath || args.path || args.AbsolutePath || args.TargetFile || "";
    const envPattern = /(^|[\\/])\.env(\.[^/\\]*)?$/;

    if (envPattern.test(filePath)) {
      console.log(JSON.stringify({
        decision: "deny",
        reason: `[env-protection] Blocked attempt to read "${filePath}". .env files may contain secrets and must not be read by agents. Use environment variable references instead.`
      }));
      process.exit(0);
    }
  }

  console.log(JSON.stringify({ decision: "allow" }));
} catch (err) {
  // Fallback to allow if something goes wrong
  console.log(JSON.stringify({ decision: "allow" }));
}
