"use client";

import { useState } from "react";
import Image from "next/image";
import { AboutModal } from "@/components/ui/AboutModal";

export function LoginHeader() {
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  return (
    <div className="flex flex-col items-center mb-8">
      <button 
        type="button"
        onClick={() => setIsAboutOpen(true)}
        className="focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-xl transition-transform hover:scale-105 active:scale-95 border-none bg-transparent p-0 cursor-pointer"
        aria-label="About Trade Journal"
      >
        <Image
          src="/logo.svg"
          alt="Trade Journal logo"
          width={512}
          height={512}
          priority
          className="rounded-xl mb-4"
          style={{ width: "auto", maxWidth: "100%", height: "auto", maxHeight: "10rem" }}
        />
      </button>
      <h1 className="text-2xl font-bold text-foreground mb-1 tracking-tight">Trade Journal</h1>
      <p className="text-muted-foreground text-sm">
        Sign in to your account
      </p>
      
      <AboutModal 
        isOpen={isAboutOpen} 
        onClose={() => setIsAboutOpen(false)} 
      />
    </div>
  );
}