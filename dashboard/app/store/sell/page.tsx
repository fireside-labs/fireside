"use client";

import SellerDashboard from "@/components/SellerDashboard";
import Link from "next/link";

export default function SellPage() {
    return (
        <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <span>💰</span> Seller Dashboard
                    </h1>
                    <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                        Create and sell agents, themes, voice packs, and more. You earn 70% of each sale.
                    </p>
                </div>
                <Link href="/store" className="text-xs text-[var(--color-neon)] hover:underline">
                    ← Back to Store
                </Link>
            </div>

            <SellerDashboard />
        </div>
    );
}
