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
