import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Valhalla Mesh — AI that learns from your work",
  description:
    "Deploy persistent AI agents on your own hardware. They use your tools, remember what works, and get smarter every day.",
  openGraph: {
    title: "Valhalla Mesh — AI that learns from your work",
    description:
      "Deploy persistent AI agents on your own hardware. They use your tools, remember what works, and get smarter every day.",
    type: "website",
    siteName: "Valhalla Mesh",
  },
  twitter: {
    card: "summary_large_image",
    title: "Valhalla Mesh",
    description:
      "AI agents that run on your hardware, learn from your work, and never forget.",
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
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
