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

/**
 * Canonical error extractor for @hey-api SDK errors.
 *
 * The SDK returns the parsed JSON body directly as `error` — FastAPI validation
 * errors have `detail` at the top level, not nested under `.response.data`.
 *
 * Usage:
 *   const { error } = await someApiFunction();
 *   setErrorMsg(extractApiError(error));
 *
 * Or in catch blocks (mutations):
 *   } catch (err) {
 *     setErrorMsg(extractApiError(err));
 *   }
 */
export function extractApiError(error: unknown, fallback = "An unexpected error occurred."): string {
  if (!error) return fallback;

  if (typeof error === "object") {
    const err = error as Record<string, unknown>;

    if (typeof err.detail === "string") return err.detail;

    if (Array.isArray(err.detail) && err.detail.length > 0) {
      const first = err.detail[0] as Record<string, unknown>;
      if (typeof first.msg === "string") return first.msg;
    }

    if (error instanceof Error) return error.message;
  }

  if (typeof error === "string") return error;

  return fallback;
}
