import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Dove | From completed work to completed paperwork", description: "The work is done. Bring the paperwork across the finish line. Use Dove in your browser with no account or paid AI API.", icons: { icon: "/favicon.svg" } };
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
