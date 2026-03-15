/**
 * 🏠 Agent Context — Sprint 10 Task 3.
 *
 * Stores the AI agent profile fetched from GET /api/v1/agent/profile.
 * Used by chat to show "Let me check with [agent name]..." flavor text.
 */
import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { companionAPI } from "./api";

interface AgentProfile {
    name: string;
    style: string;
    status: "online" | "offline";
    uptime?: string;
}

interface AgentContextValue {
    agent: AgentProfile;
    isAgentLoaded: boolean;
}

const defaultAgent: AgentProfile = { name: "Atlas", style: "analytical", status: "offline" };

const AgentContext = createContext<AgentContextValue>({
    agent: defaultAgent,
    isAgentLoaded: false,
});

export function AgentProvider({ children }: { children: ReactNode }) {
    const [agent, setAgent] = useState<AgentProfile>(defaultAgent);
    const [isAgentLoaded, setIsAgentLoaded] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const res = await companionAPI.agentProfile();
                if (res.name) {
                    setAgent({
                        name: res.name,
                        style: res.style || "analytical",
                        status: "online",
                        uptime: res.uptime,
                    });
                }
            } catch {
                // API unavailable — use defaults
            }
            setIsAgentLoaded(true);
        })();
    }, []);

    return (
        <AgentContext.Provider value={{ agent, isAgentLoaded }}>
            {children}
        </AgentContext.Provider>
    );
}

export function useAgent() {
    return useContext(AgentContext);
}
