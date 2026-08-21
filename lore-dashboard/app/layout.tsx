import type {Metadata} from "next";
import {Figtree} from "next/font/google";
import type {ReactNode} from "react";
import "./globals.css";

const figtree = Figtree({subsets: ["latin"], variable: "--font-figtree"});

export const metadata: Metadata = {
  title: "LORE Security Control Center",
  description: "Security telemetry and protection demos for LORE"
};

export default function RootLayout({children}: {children: ReactNode}) {
  return (
    <html lang="en">
      <body className={figtree.variable}>{children}</body>
    </html>
  );
}
