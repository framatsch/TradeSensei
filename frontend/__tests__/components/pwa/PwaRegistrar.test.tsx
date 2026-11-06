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
import { render } from "@testing-library/react";
import { PwaRegistrar } from "@/components/pwa/PwaRegistrar";
import manifest from "@/app/manifest";

describe("PWA Manifest and Service Worker Registrar", () => {
  it("exports a valid standalone Web App Manifest with 192x192, 512x512, and maskable icons", () => {
    const data = manifest();
    expect(data.name).toBe("Trade Sensei");
    expect(data.short_name).toBe("Trade Sensei");
    expect(data.display).toBe("standalone");
    expect(data.start_url).toBe("/dashboard");
    expect(data.background_color).toBe("#0a0a14");
    expect(data.theme_color).toBe("#131317");
    expect(data.icons).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ src: "/icons/icon-192x192.png", sizes: "192x192", purpose: "any" }),
        expect.objectContaining({ src: "/icons/icon-512x512.png", sizes: "512x512", purpose: "any" }),
        expect.objectContaining({ src: "/icons/icon-maskable-512x512.png", sizes: "512x512", purpose: "maskable" }),
      ])
    );
  });

  it("registers /sw.js when navigator.serviceWorker is available", () => {
    const registerMock = jest.fn().mockResolvedValue({});
    Object.defineProperty(window.navigator, "serviceWorker", {
      value: { register: registerMock },
      configurable: true,
    });

    render(<PwaRegistrar />);
    expect(registerMock).toHaveBeenCalledWith("/sw.js");
  });
});
