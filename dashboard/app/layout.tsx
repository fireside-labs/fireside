import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { ToastProvider } from "@/components/Toast";
import { ThemeProvider } from "@/components/ThemeToggle";
import { OnboardingGate } from "@/components/OnboardingGate";

export const metadata: Metadata = {
    title: "Valhalla — Mission Control",
    description: "AI mesh dashboard — nodes, models, souls, and plugins",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link
                    rel="preconnect"
                    href="https://fonts.gstatic.com"
                    crossOrigin="anonymous"
                />
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body className="bg-[var(--color-void)] text-[var(--color-rune)] antialiased">
                <ThemeProvider>
                    <ToastProvider>
                        <OnboardingGate />
                        <div className="flex min-h-screen">
                            <Sidebar />
                            <main className="main-content flex-1 ml-64 p-8">{children}</main>
                        </div>
                    </ToastProvider>
                </ThemeProvider>
            </body>
        </html>
    );
}
