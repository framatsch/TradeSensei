import { client } from "@/lib/api/client.gen";
import { registerApiInterceptors, resetInterceptors } from "@/lib/apiInterceptors";

jest.mock("@/lib/api/client.gen", () => ({
  client: {
    interceptors: {
      request: { clear: jest.fn(), use: jest.fn() },
      response: { clear: jest.fn(), use: jest.fn() },
      error: { clear: jest.fn(), use: jest.fn() },
    },
  },
}));

describe("registerApiInterceptors", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    resetInterceptors();
  });

  it("should be idempotent and only register interceptors once", () => {
    registerApiInterceptors();
    registerApiInterceptors();
    registerApiInterceptors();

    expect(client.interceptors.request.use).toHaveBeenCalledTimes(1);
    expect(client.interceptors.response.use).toHaveBeenCalledTimes(1);
    expect(client.interceptors.error.use).toHaveBeenCalledTimes(1);
  });

  it("should register all three interceptors on first call", () => {
    registerApiInterceptors();

    expect(client.interceptors.request.use).toHaveBeenCalledTimes(1);
    expect(client.interceptors.response.use).toHaveBeenCalledTimes(1);
    expect(client.interceptors.error.use).toHaveBeenCalledTimes(1);
  });
});
