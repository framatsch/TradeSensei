/** @type {import("@hey-api/openapi-ts").UserConfig} */
export default {
  input: "http://localhost:8000/openapi.json",
  output: "./lib/api",
  plugins: [
    {
      name: "@hey-api/client-fetch",
      // Use the Next.js proxy as default — avoids the localhost:8000 timing
      // dependency on initializeApiClient() and survives regeneration.
      baseUrl: "/api/proxy",
    },
  ],
};
