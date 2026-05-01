import { renderHook, act } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useUploadScreenshot, useDeleteScreenshot } from "../../hooks/useScreenshots";

// Mock the generated API client functions
jest.mock("@/lib/api/index", () => ({
  uploadScreenshotApiV1TradesTradeIdScreenshotsPost: jest.fn(),
  deleteScreenshotApiV1TradesTradeIdScreenshotsFilenameDelete: jest.fn(),
}));

import {
  uploadScreenshotApiV1TradesTradeIdScreenshotsPost,
  deleteScreenshotApiV1TradesTradeIdScreenshotsFilenameDelete,
} from "@/lib/api/index";

const mockUpload = uploadScreenshotApiV1TradesTradeIdScreenshotsPost as jest.Mock;
const mockDelete = deleteScreenshotApiV1TradesTradeIdScreenshotsFilenameDelete as jest.Mock;

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return Wrapper;
}

const TRADE_ID = "trade-abc-123";

describe("useUploadScreenshot", () => {
  beforeEach(() => {
    mockUpload.mockReset();
  });

  it("calls the upload API with the correct trade_id and file", async () => {
    const updatedTrade = { id: TRADE_ID, image_urls: ["/uploads/test.png"] };
    mockUpload.mockResolvedValue({ data: { data: updatedTrade }, error: null });

    const { result } = renderHook(() => useUploadScreenshot(TRADE_ID), {
      wrapper: makeWrapper(),
    });

    const file = new File(["content"], "chart.png", { type: "image/png" });

    await act(async () => {
      result.current.mutate(file);
    });

    expect(mockUpload).toHaveBeenCalledWith(
      expect.objectContaining({
        path: { trade_id: TRADE_ID },
        body: { file },
      })
    );
  });

  it("throws when the API returns an error", async () => {
    const apiError = new Error("Storage not configured");
    mockUpload.mockResolvedValue({ data: null, error: apiError });

    const { result } = renderHook(() => useUploadScreenshot(TRADE_ID), {
      wrapper: makeWrapper(),
    });

    const file = new File(["content"], "chart.png", { type: "image/png" });
    let caughtError: Error | null = null;

    await act(async () => {
      result.current.mutate(file, {
        onError: (e) => { caughtError = e; },
      });
    });

    expect(caughtError).toBeTruthy();
    expect((caughtError as Error).message).toBe("Storage not configured");
  });
});

describe("useDeleteScreenshot", () => {
  beforeEach(() => {
    mockDelete.mockReset();
  });

  it("extracts filename and calls delete API", async () => {
    const updatedTrade = { id: TRADE_ID, image_urls: [] };
    mockDelete.mockResolvedValue({ data: { data: updatedTrade }, error: null });

    const { result } = renderHook(() => useDeleteScreenshot(TRADE_ID), {
      wrapper: makeWrapper(),
    });

    const fullUrl = "https://storage.example.com/uploads/trade-abc-123/chart.png";

    await act(async () => {
      result.current.mutate(fullUrl);
    });

    expect(mockDelete).toHaveBeenCalledWith(
      expect.objectContaining({
        path: { trade_id: TRADE_ID, filename: "chart.png" },
      })
    );
  });
});
