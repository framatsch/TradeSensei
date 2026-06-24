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

import { useEffect, useState, useRef } from "react";
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react";

interface Props {
  urls: string[];
  initialIndex?: number;
  onClose: () => void;
}

export function CheckinLightbox({ urls, initialIndex = 0, onClose }: Props) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  // Reset scale and position when index changes
  useEffect(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  }, [currentIndex]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") handlePrev();
      if (e.key === "ArrowRight") handleNext();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex, urls.length, onClose]);

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : urls.length - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < urls.length - 1 ? prev + 1 : 0));
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (scale > 1) {
      e.preventDefault();
      setIsDragging(true);
      dragStart.current = { x: e.clientX - position.x, y: e.clientY - position.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && scale > 1) {
      setPosition({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (scale > 1 && e.touches.length === 1) {
      setIsDragging(true);
      dragStart.current = { x: e.touches[0].clientX - position.x, y: e.touches[0].clientY - position.y };
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (isDragging && scale > 1 && e.touches.length === 1) {
      // Prevent default scrolling when panning a zoomed image
      if (e.cancelable) e.preventDefault();
      setPosition({
        x: e.touches[0].clientX - dragStart.current.x,
        y: e.touches[0].clientY - dragStart.current.y,
      });
    }
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      // Scroll up -> Zoom in
      setScale((s) => Math.min(4, s + 0.15));
    } else if (e.deltaY > 0) {
      // Scroll down -> Zoom out
      setScale((s) => {
        const newScale = Math.max(0.5, s - 0.15);
        if (newScale <= 1) setPosition({ x: 0, y: 0 });
        return newScale;
      });
    }
  };

  const resetZoom = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  if (!urls || urls.length === 0) return null;

  return (
    <div
      className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4 sm:p-8"
      onClick={onClose}
    >
      {/* Top right close button */}
      <button
        type="button"
        onClick={onClose}
        className="absolute top-4 right-4 p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors z-50"
      >
        <X className="w-6 h-6" />
      </button>

      {/* Navigation buttons */}
      {urls.length > 1 && (
        <>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handlePrev();
            }}
            className="absolute left-4 p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors z-50"
          >
            <ChevronLeft className="w-8 h-8" />
          </button>
          
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleNext();
            }}
            className="absolute right-4 p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors z-50"
          >
            <ChevronRight className="w-8 h-8" />
          </button>
        </>
      )}

      {/* Main Image Container */}
      <div
        className="relative w-full h-full flex flex-col items-center justify-center overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div 
          className={`flex-1 flex items-center justify-center w-full min-h-0 touch-none ${scale > 1 ? 'cursor-grab active:cursor-grabbing' : ''}`}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onTouchCancel={handleTouchEnd}
          onWheel={handleWheel}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={urls[currentIndex]}
            alt={`Full size screenshot ${currentIndex + 1}`}
            className="max-w-none transition-transform duration-75 ease-out select-none pointer-events-none"
            style={{ 
              transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
              maxHeight: scale === 1 ? '85vh' : 'none',
              maxWidth: scale === 1 ? '100%' : 'none'
            }}
            draggable={false}
          />
        </div>
        
        {/* Controls */}
        <div className="flex flex-col items-center gap-4 mt-4 z-50">
          {/* Zoom Controls */}
          <div className="flex items-center gap-2 bg-black/50 backdrop-blur-sm rounded-full p-1 border border-white/10">
            <button
              type="button"
              onClick={() => setScale((s) => Math.max(0.5, s - 0.25))}
              className="p-2 text-white hover:bg-white/20 rounded-full transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-5 h-5" />
            </button>
            <button
              type="button"
              onClick={resetZoom}
              className="p-2 text-white hover:bg-white/20 rounded-full transition-colors flex items-center justify-center min-w-[48px] text-xs font-medium"
              title="Reset Zoom"
            >
              {Math.round(scale * 100)}%
            </button>
            <button
              type="button"
              onClick={() => setScale((s) => Math.min(4, s + 0.25))}
              className="p-2 text-white hover:bg-white/20 rounded-full transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-5 h-5" />
            </button>
          </div>

          {/* Indicator */}
          {urls.length > 1 && (
            <div className="text-white/70 text-sm font-medium tracking-wide">
              {currentIndex + 1} / {urls.length}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
