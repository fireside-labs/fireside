import type { MeshNode } from "@/lib/api";

const ROLE_ICONS: Record<string, string> = {
    orchestrator: "👑",
    backend: "🔨",
    memory: "🧠",
    security: "🛡️",
    courier: "📨",
};

export function NodeCard({ node }: { node: MeshNode }) {
    const isOnline = node.status === "online";

    return (
        <div className="glass-card p-6 flex flex-col gap-4">
            {/* ─── Header ─── */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <span className="text-2xl">{ROLE_ICONS[node.role] || "⬡"}</span>
                    <div>
                        <h3 className="text-white font-semibold text-lg capitalize">{node.name}</h3>
                        <p className="text-xs text-[var(--color-rune-dim)] capitalize">{node.role}</p>
                    </div>
                </div>
                <div className={isOnline ? "status-online" : "status-offline"} />
            </div>

            {/* ─── Details ─── */}
            <div className="space-y-2.5 text-sm">
                <DetailRow label="Status" value={isOnline ? "Online" : "Offline"} accent={isOnline} />
                <DetailRow label="Model" value={node.current_model} />
                <DetailRow label="Last Task" value={node.last_task} />
                <DetailRow label="Uptime" value={node.uptime} />
                <DetailRow label="Address" value={`${node.ip}:${node.port}`} />
            </div>
        </div>
    );
}

function DetailRow({
    label,
    value,
    accent,
}: {
    label: string;
    value: string;
    accent?: boolean;
}) {
    return (
        <div className="flex justify-between items-center">
            <span className="text-[var(--color-rune-dim)]">{label}</span>
            <span className={accent ? "text-[var(--color-neon)] font-medium" : "text-white"}>
                {value}
            </span>
        </div>
    );
}
