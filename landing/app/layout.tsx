import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fireside — The only AI that's actually yours",
  description:
    "ChatGPT forgets you. Copilot rents you cloud time. Fireside lives on your machine — it remembers every conversation, learns your preferences, and gets smarter the longer you use it. Free forever.",
  openGraph: {
    title: "Fireside — The only AI that's actually yours",
    description:
      "An AI that lives on your machine, remembers everything, and gets smarter every day. Free forever, no cloud.",
    type: "website",
    siteName: "Fireside",
  },
  twitter: {
    card: "summary_large_image",
    title: "Fireside — The only AI that's actually yours",
    description:
      "ChatGPT forgets you. Copilot rents you cloud time. Fireside lives on your machine. Free forever.",
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
