import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Trade Journal",
  description: "Statistical analysis and visualization of trading data",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-900 text-slate-100 antialiased min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
