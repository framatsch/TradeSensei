"use client";

import { useEffect } from "react";
import { useAppContext } from "@/hooks/useAppContext";
import { AppContext } from "@/stores/appContextStore";

export function ContextSetter({ context }: { context: AppContext }) {
  const { setActiveContext } = useAppContext();

  useEffect(() => {
    setActiveContext(context);
  }, [context, setActiveContext]);

  return null;
}
