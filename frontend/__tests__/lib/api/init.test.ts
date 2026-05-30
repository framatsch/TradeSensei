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

import { client } from "@/lib/api/client.gen";
import { registerApiInterceptors, resetInterceptors } from "@/lib/apiInterceptors";

jest.mock("@/lib/api/client.gen", () => ({
  client: {
    setConfig: jest.fn(),
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
