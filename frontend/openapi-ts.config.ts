/** @type {import("@hey-api/openapi-ts").UserConfig} */
export default {
  input: "http://localhost:8000/openapi.json",
  output: "./lib/api",
  client: "@hey-api/client-fetch",
  base: "/api/proxy",
};
