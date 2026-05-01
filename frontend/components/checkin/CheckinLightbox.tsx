"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

interface Props {
  url: string;
  onClose: () => void;
}

export function CheckinLightbox({ url, onClose }: Props) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4 sm:p-8"
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors z-50"
      >
        <X className="w-6 h-6" />
      </button>
      
      <div
        className="relative max-w-full max-h-full"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          src={url}
          alt="Full size screenshot"
          className="max-w-full max-h-[90vh] object-contain rounded-md shadow-2xl"
        />
      </div>
    </div>
  );
}
