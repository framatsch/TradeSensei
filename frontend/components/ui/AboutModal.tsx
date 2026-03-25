"use client";

import { Logo } from "./Logo";

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
  version?: string;
  appName?: string;
  license?: string;
}

export function AboutModal({
  isOpen,
  onClose,
  version = "0.1.0",
  appName = "Trade Journal",
  license = "MIT License",
}: AboutModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-card rounded-2xl border border-border shadow-2xl p-8 w-full max-w-sm mx-4 flex flex-col items-center text-center animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 transform hover:scale-105 transition-transform duration-300">
          <Logo size={120} className="shadow-lg rounded-2xl border-none" />
        </div>
        
        <h2 className="text-2xl font-bold text-foreground mb-1">{appName}</h2>
        <p className="text-sm text-muted-foreground mb-6 font-medium">Statistical Analysis & Visualization</p>
        
        <div className="w-full space-y-3 mb-8 bg-muted/30 p-4 rounded-xl border border-border/50">
          <div className="flex justify-between items-center text-sm">
            <span className="text-muted-foreground">Version</span>
            <span className="font-mono font-semibold text-foreground bg-background px-2 py-0.5 rounded border border-border">{version}</span>
          </div>
          <div className="flex justify-between items-center text-sm">
            <span className="text-muted-foreground">License</span>
            <span className="font-medium text-foreground">{license}</span>
          </div>
        </div>
        
        <button
          type="button"
          onClick={onClose}
          className="w-full py-2.5 rounded-xl text-sm font-semibold bg-primary hover:bg-primary/90 text-white shadow-md hover:shadow-lg transition-all duration-200"
        >
          Close
        </button>
        
        <p className="mt-6 text-[10px] text-muted-foreground uppercase tracking-widest font-bold">
          &copy; {new Date().getFullYear()} {appName}
        </p>
      </div>
      
      {/* Backdrop click to close */}
      <div className="absolute inset-0 -z-10" onClick={onClose} />
    </div>
  );
}
