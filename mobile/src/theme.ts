/**
 * Valhalla Design System — Mobile
 *
 * Dark premium aesthetic matching the dashboard.
 * Deep dark backgrounds, neon green accents, glassmorphism cards.
 */

export const colors = {
    // Backgrounds
    bgPrimary: "#0a0a0f",
    bgSecondary: "#111118",
    bgCard: "rgba(255, 255, 255, 0.04)",
    bgCardHover: "rgba(255, 255, 255, 0.08)",
    bgInput: "rgba(255, 255, 255, 0.06)",

    // Accent
    neon: "#00ff88",
    neonDim: "rgba(0, 255, 136, 0.6)",
    neonGlow: "rgba(0, 255, 136, 0.08)",
    neonBorder: "rgba(0, 255, 136, 0.15)",

    // Status bars
    happinessHigh: "#2ecc71",
    happinessMid: "#f39c12",
    happinessLow: "#e74c3c",

    // Text
    textPrimary: "#ffffff",
    textSecondary: "rgba(255, 255, 255, 0.7)",
    textDim: "rgba(255, 255, 255, 0.4)",
    textMuted: "rgba(255, 255, 255, 0.25)",

    // States
    warning: "#f39c12",
    danger: "#ff4466",
    success: "#00ff88",
    info: "#3b82f6",

    // Borders
    glassBorder: "rgba(255, 255, 255, 0.08)",
    cardBorder: "rgba(255, 255, 255, 0.06)",

    // Tab bar
    tabInactive: "rgba(255, 255, 255, 0.3)",
    tabActive: "#00ff88",
    tabBg: "#0d0d14",

    // Offline
    offlineDot: "rgba(255, 68, 102, 0.6)",
    onlineDot: "#00ff88",
} as const;

export const spacing = {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    xxl: 24,
    xxxl: 32,
} as const;

export const borderRadius = {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    full: 9999,
} as const;

export const fontSize = {
    tiny: 9,
    xs: 10,
    sm: 12,
    md: 14,
    lg: 16,
    xl: 18,
    xxl: 22,
    hero: 28,
} as const;

export const shadows = {
    card: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 4,
    },
    glow: {
        shadowColor: "#00ff88",
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.3,
        shadowRadius: 12,
        elevation: 6,
    },
} as const;
