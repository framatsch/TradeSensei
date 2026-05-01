/**
 * Simple debounce hook — delays updating a value until the user stops
 * changing it for `delay` milliseconds.
 */

"use client";

import { useState, useEffect } from "react";

export function useDebounce<T>(value: T, delay: number = 400): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}