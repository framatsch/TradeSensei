"use client";

import { useEffect } from "react";
import { useAppContext } from "@/hooks/useAppContext";
import { AppContext } from "@/stores/appContextStore";

export function ContextSetter({ context }: { context: AppContext }) {
  const { activeContext, setActiveContext } = useAppContext();

  useEffect(() => {
    if (activeContext !== context) {
      setActiveContext(context);
    }
  }, [activeContext, context, setActiveContext]);

  return null;
}
