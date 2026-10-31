/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { TradeImageGallery } from "@/components/trades/TradeImageGallery";

describe("TradeImageGallery", () => {
  it("shows empty state when no images are provided", () => {
    render(<TradeImageGallery imageUrls={[]} />);
    expect(screen.getByText("No images attached.")).toBeInTheDocument();
    expect(screen.getByText("Trade Images")).toBeInTheDocument();
  });

  it("renders thumbnails for each image URL", () => {
    const urls = [
      "https://storage.example.com/trade/img1.png",
      "https://storage.example.com/trade/img2.png",
    ];
    render(<TradeImageGallery imageUrls={urls} />);

    const imgs = screen.getAllByRole("img", { name: "Trade image" });
    expect(imgs).toHaveLength(2);
    expect(imgs[0]).toHaveAttribute("src", `/api/storage-proxy?url=${encodeURIComponent(urls[0])}`);
    expect(imgs[1]).toHaveAttribute("src", `/api/storage-proxy?url=${encodeURIComponent(urls[1])}`);
  });

  it("opens lightbox when a thumbnail button is clicked", () => {
    const urls = ["https://storage.example.com/trade/chart.png"];
    render(<TradeImageGallery imageUrls={urls} />);

    // Lightbox not visible initially
    expect(screen.getAllByRole("img", { name: "Trade image" })).toHaveLength(1);

    // Click the thumbnail button
    const btn = screen.getByRole("button");
    fireEvent.click(btn);

    // Now there should be 2 img elements: thumbnail + lightbox
    expect(screen.getAllByRole("img", { name: "Trade image" })).toHaveLength(2);
    expect(screen.getAllByRole("img", { name: "Trade image" })[1]).toHaveAttribute(
      "src",
      `/api/storage-proxy?url=${encodeURIComponent(urls[0])}`,
    );
  });

  it("closes lightbox when Escape key is pressed (second test variant)", () => {
    const urls = ["https://storage.example.com/trade/chart.png"];
    const { container } = render(<TradeImageGallery imageUrls={urls} />);

    // Open lightbox
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getAllByRole("img", { name: "Trade image" })).toHaveLength(2);

    // Find the fixed backdrop (has class "fixed") and click it
    const backdrop = container.querySelector(".fixed");
    if (backdrop) fireEvent.click(backdrop);

    // Lightbox closed
    expect(screen.getAllByRole("img", { name: "Trade image" })).toHaveLength(1);
  });

  it("closes lightbox on Escape key", () => {
    const urls = ["https://storage.example.com/trade/chart.png"];
    render(<TradeImageGallery imageUrls={urls} />);

    // Open lightbox
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getAllByRole("img", { name: "Trade image" })).toHaveLength(2);

    // Press Escape
    fireEvent.keyDown(window, { key: "Escape" });

    expect(screen.getAllByRole("img", { name: "Trade image" })).toHaveLength(1);
  });
});
