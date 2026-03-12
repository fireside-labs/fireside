import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fireside — AI that learns while you sleep",
  description:
    "Deploy persistent AI agents on your own hardware. They dream, learn, and wake up smarter every morning. No cloud required.",
  openGraph: {
    title: "Fireside — AI that learns while you sleep",
    description:
      "Deploy persistent AI agents on your own hardware. They dream, learn, and wake up smarter every morning.",
    type: "website",
    siteName: "Fireside",
  },
  twitter: {
    card: "summary_large_image",
    title: "Fireside — AI that learns while you sleep",
    description:
      "Persistent AI agents that run on your hardware, learn from your work, and never forget.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&family=Playfair+Display:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
