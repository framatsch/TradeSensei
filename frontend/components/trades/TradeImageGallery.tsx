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

"use client";

import { useEffect, useState } from "react";
import { resolveStorageUrl } from "@/lib/storageUrl";

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
      <div className="solid-card p-5 shadow-sm">
        <h2 className="text-base font-semibold text-foreground mb-2">Trade Images</h2>
        <p className="text-sm text-muted-foreground">No images attached.</p>
      </div>
    );
  }

  return (
    <div className="solid-card p-5 shadow-sm">
      <h2 className="text-base font-semibold text-foreground mb-4">Trade Images</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {imageUrls.map((url) => (
          <button
            type="button"
            key={url}
            className="rounded-lg overflow-hidden border border-border bg-secondary aspect-[4/3]"
            onClick={() => setActiveImage(resolveStorageUrl(url))}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={resolveStorageUrl(url)} alt="Trade image" className="w-full h-full object-cover" />
          </button>
        ))}
      </div>
      {activeImage && <Lightbox src={activeImage} onClose={() => setActiveImage(null)} />}
    </div>
  );
}
