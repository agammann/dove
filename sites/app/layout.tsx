import "./globals.css";
export const metadata = { title: "Dove | From completed work to completed paperwork", description: "No-account paperwork workspace. Device analysis and manual review need no API key; optional OpenAI analysis uses your own key and API billing.", icons: { icon: "/favicon.svg" } };
export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
