/**
 * Companion Mode context.
 *
 * Pet Mode (default): Chat, Care, Brain, Skills, Personality — full gamification.
 * Tool Mode: Chat, Tools, Tasks, Brain, Personality — no gamification.
 *
 * Persisted in AsyncStorage.
 */
import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

export type CompanionMode = "pet" | "tool";

const MODE_KEY = "fireside_companion_mode";

interface ModeContextType {
    mode: CompanionMode;
    setMode: (mode: CompanionMode) => void;
    isPetMode: boolean;
    isToolMode: boolean;
}

const ModeContext = createContext<ModeContextType>({
    mode: "pet",
    setMode: () => { },
    isPetMode: true,
    isToolMode: false,
});

export function ModeProvider({ children }: { children: ReactNode }) {
    const [mode, setModeState] = useState<CompanionMode>("pet");

    useEffect(() => {
        AsyncStorage.getItem(MODE_KEY).then((stored) => {
            if (stored === "pet" || stored === "tool") setModeState(stored);
        });
    }, []);

    const setMode = (newMode: CompanionMode) => {
        setModeState(newMode);
        AsyncStorage.setItem(MODE_KEY, newMode);
    };

    return (
        <ModeContext.Provider
            value={{
                mode,
                setMode,
                isPetMode: mode === "pet",
                isToolMode: mode === "tool",
            }}
        >
            {children}
        </ModeContext.Provider>
    );
}

export function useMode() {
    return useContext(ModeContext);
}
