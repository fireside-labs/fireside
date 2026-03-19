"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
    id: number;
    message: string;
    type: ToastType;
    hiding: boolean;
}

interface ToastContextValue {
    toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => { } });

export function useToast() {
    return useContext(ToastContext);
}

let toastId = 0;
const MAX_TOASTS = 3;

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const dismiss = useCallback((id: number) => {
        setToasts((prev) => prev.map((t) => t.id === id ? { ...t, hiding: true } : t));
        setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 300);
    }, []);

    const toast = useCallback((message: string, type: ToastType = "success") => {
        const id = ++toastId;
        // Cap at MAX_TOASTS — drop oldest if exceeded
        setToasts((prev) => {
            const next = [...prev, { id, message, type, hiding: false }];
            return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next;
        });

        // Start hide animation after 2.7s
        setTimeout(() => {
            setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, hiding: true } : t)));
        }, 2700);

        // Remove after 3s
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 3000);
    }, []);

    const colorMap: Record<ToastType, string> = {
        success: "toast-success",
        error: "toast-error",
        info: "toast-info",
        warning: "toast-warning",
    };

    return (
        <ToastContext.Provider value={{ toast }}>
            {children}
            <div className="toast-container" role="status" aria-live="polite">
                {toasts.map((t, i) => (
                    <div
                        key={t.id}
                        className={"toast " + colorMap[t.type] + (t.hiding ? " hiding" : "")}
                        style={{ bottom: 24 + i * 60 + "px", cursor: "pointer", display: "flex", alignItems: "center", gap: 10 }}
                        onClick={() => dismiss(t.id)}
                        title="Click to dismiss"
                    >
                        <span style={{ flex: 1 }}>{t.message}</span>
                        <span style={{ opacity: 0.5, fontSize: 12, flexShrink: 0 }}>✕</span>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}
