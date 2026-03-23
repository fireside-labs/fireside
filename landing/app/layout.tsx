import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fireside — Your free personal AI assistant",
  description:
    "Create presentations, search your files, draft emails, and talk to it with your voice — completely private, no subscription. Download free for Windows, Mac, and Linux.",
  openGraph: {
    title: "Fireside — Your free personal AI assistant",
    description:
      "An AI assistant that creates presentations, remembers your files, and gets smarter every day. Free and private.",
    type: "website",
    siteName: "Fireside",
  },
  twitter: {
    card: "summary_large_image",
    title: "Fireside — Your free personal AI assistant",
    description:
      "Create presentations, search your files, and talk to your AI with your voice. Free, private, no subscription.",
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
