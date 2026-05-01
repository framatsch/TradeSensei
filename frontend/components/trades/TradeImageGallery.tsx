"use client";

import { useEffect, useState } from "react";

function Lightbox({ src, onClose }: { src: string; onClose: () => void }) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4" onClick={onClose}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt="Trade image"
        className="max-w-full max-h-full rounded-lg object-contain"
        onClick={(event) => event.stopPropagation()}
      />
    </div>
  );
}

interface TradeImageGalleryProps {
  imageUrls: string[];
}

export function TradeImageGallery({ imageUrls }: TradeImageGalleryProps) {
  const [activeImage, setActiveImage] = useState<string | null>(null);

  if (imageUrls.length === 0) {
    return (
      <div className="bg-card rounded-xl border border-border p-5 shadow-sm">
        <h2 className="text-base font-semibold text-foreground mb-2">Trade Images</h2>
        <p className="text-sm text-muted-foreground">No images attached.</p>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-xl border border-border p-5 shadow-sm">
      <h2 className="text-base font-semibold text-foreground mb-4">Trade Images</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {imageUrls.map((url) => (
          <button
            type="button"
            key={url}
            className="rounded-lg overflow-hidden border border-border bg-secondary aspect-[4/3]"
            onClick={() => setActiveImage(url)}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={url} alt="Trade image" className="w-full h-full object-cover" />
          </button>
        ))}
      </div>
      {activeImage && <Lightbox src={activeImage} onClose={() => setActiveImage(null)} />}
    </div>
  );
}
