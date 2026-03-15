/**
 * Fireside Design System — Mobile
 *
 * Sprint 8: Updated from neon-green to fire-orange palette per CREATIVE_DIRECTION.md.
 * Warm amber fire palette — campfire aesthetic.
 *
 * Brand tokens:
 *   --fire-orange:    #E8712C  (primary accent, CTA buttons)
 *   --ember-gold:     #F5A623  (highlights, progress, XP)
 *   --warm-glow:      #FFF3E0  (subtle backgrounds)
 *   --deep-charcoal:  #1A1A2E  (primary bg)
 *   --midnight:       #0D0D1A  (deepest bg)
 *   --ash-gray:       #8E8E93  (secondary text)
 *   --snow:           #F5F5F7  (primary text)
 */

export const colors = {
    // Backgrounds
    bgPrimary: "#0D0D1A",      // --midnight (deepest)
    bgSecondary: "#1A1A2E",    // --deep-charcoal
    bgCard: "rgba(255, 255, 255, 0.04)",
    bgCardHover: "rgba(255, 255, 255, 0.08)",
    bgInput: "rgba(255, 255, 255, 0.06)",

    // Fire accent (was neon-green #00ff88)
    neon: "#E8712C",           // --fire-orange (primary accent)
    neonDim: "rgba(232, 113, 44, 0.6)",
    neonGlow: "rgba(232, 113, 44, 0.08)",
    neonBorder: "rgba(232, 113, 44, 0.15)",

    // Ember highlight
    ember: "#F5A623",          // --ember-gold
    emberGlow: "rgba(245, 166, 35, 0.08)",
    warmGlow: "#FFF3E0",       // --warm-glow

    // Status bars
    happinessHigh: "#2ecc71",
    happinessMid: "#F5A623",   // ember-gold instead of generic orange
    happinessLow: "#e74c3c",

    // Text (updated to brand snow)
    textPrimary: "#F5F5F7",    // --snow
    textSecondary: "rgba(245, 245, 247, 0.7)",
    textDim: "rgba(245, 245, 247, 0.4)",
    textMuted: "rgba(245, 245, 247, 0.25)",

    // States
    warning: "#F5A623",        // ember-gold
    danger: "#ff4466",
    success: "#2ecc71",
    info: "#3b82f6",

    // Borders
    glassBorder: "rgba(255, 255, 255, 0.08)",
    cardBorder: "rgba(255, 255, 255, 0.06)",

    // Tab bar
    tabInactive: "rgba(245, 245, 247, 0.3)",
    tabActive: "#E8712C",      // fire-orange
    tabBg: "#0D0D1A",          // midnight

    // Connection status
    offlineDot: "rgba(255, 68, 102, 0.6)",
    onlineDot: "#2ecc71",
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
        shadowColor: "#E8712C", // fire-orange glow
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.3,
        shadowRadius: 12,
        elevation: 6,
    },
    ember: {
        shadowColor: "#F5A623", // ember-gold glow
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.25,
        shadowRadius: 10,
        elevation: 5,
    },
} as const;
