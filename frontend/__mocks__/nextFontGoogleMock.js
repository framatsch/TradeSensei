module.exports = new Proxy(
  {},
  {
    get: () => () => ({
      className: "mock-font",
      variable: "--mock-font",
      style: { fontFamily: "mock" },
    }),
  }
);
