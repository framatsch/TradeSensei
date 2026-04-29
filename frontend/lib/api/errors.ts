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

  // @hey-api named SDK functions: error is the parsed response body
  if (typeof error === "object") {
    const err = error as Record<string, unknown>;

    // FastAPI standard: { detail: string }
    if (typeof err.detail === "string") return err.detail;

    // FastAPI validation errors: { detail: [{ msg: string }] }
    if (Array.isArray(err.detail) && err.detail.length > 0) {
      const first = err.detail[0] as Record<string, unknown>;
      if (typeof first.msg === "string") return first.msg;
    }

    // Fallback: plain Error instance (e.g. thrown manually)
    if (error instanceof Error) return error.message;
  }

  if (typeof error === "string") return error;

  return fallback;
}
