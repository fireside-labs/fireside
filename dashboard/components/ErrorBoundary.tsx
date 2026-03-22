"use client";

import { Component, ReactNode } from "react";

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error?: Error;
}

export default class ErrorBoundary extends Component<Props, State> {
    state: State = { hasError: false };

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        console.error("[ErrorBoundary]", error, info.componentStack);
    }

    render() {
        if (this.state.hasError) {
            return this.props.fallback || (
                <div style={{
                    padding: 24, borderRadius: 12,
                    background: 'rgba(239,68,68,0.06)',
                    border: '1px solid rgba(239,68,68,0.15)',
                    color: '#F87171', fontSize: 13,
                    fontFamily: "'Outfit', system-ui",
                }}>
                    <p style={{ fontWeight: 700, marginBottom: 8 }}>⚠ Component failed to load</p>
                    <p style={{ fontSize: 11, color: '#5A4D40' }}>
                        {this.state.error?.message || "Unknown error"}
                    </p>
                    <button
                        onClick={() => this.setState({ hasError: false })}
                        style={{
                            marginTop: 12, padding: '6px 16px', borderRadius: 8,
                            border: '1px solid rgba(239,68,68,0.2)',
                            background: 'rgba(239,68,68,0.08)', color: '#F87171',
                            fontSize: 11, fontWeight: 700, cursor: 'pointer',
                            fontFamily: "'Outfit', system-ui",
                        }}
                    >
                        Retry
                    </button>
                </div>
            );
        }
        return this.props.children;
    }
}
