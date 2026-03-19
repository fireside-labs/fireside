"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// /soul is a legacy stub — redirect to the actual personality editor
export default function SoulRedirectPage() {
    const router = useRouter();
    useEffect(() => { router.replace("/personality"); }, [router]);
    return null;
}
