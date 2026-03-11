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

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const toast = useCallback((message: string, type: ToastType = "success") => {
        const id = ++toastId;
        setToasts((prev) => [...prev, { id, message, type, hiding: false }]);

        // Start hide animation after 2.7s
        setTimeout(() => {
            setToasts((prev) =>
                prev.map((t) => (t.id === id ? { ...t, hiding: true } : t))
            );
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
                        style={{ bottom: 24 + i * 60 + "px" }}
                    >
                        {t.message}
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}
