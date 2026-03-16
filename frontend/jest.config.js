/** @type {import('jest').Config} */
const config = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  transform: {
    "^.+\\.(js|jsx|ts|tsx)$": ["babel-jest", { configFile: "./babel.config.js" }],
  },
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
    "^.+\\.module\\.(css|sass|scss)$": "identity-obj-proxy",
    "^.+\\.(png|jpg|jpeg|gif|svg|ico|webp)$": "<rootDir>/__mocks__/fileMock.js",
  },
  testMatch: ["**/__tests__/**/*.[jt]s?(x)"],
  moduleFileExtensions: ["ts", "tsx", "js", "jsx", "json"],
  // react-markdown and remark-gfm are ESM — mock them entirely in tests
  transformIgnorePatterns: ["/node_modules/"],
};

module.exports = config;
