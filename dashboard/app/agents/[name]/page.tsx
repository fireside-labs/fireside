import AgentClient from "./AgentClient";

export function generateStaticParams() {
    return [
        { name: "thor" },
        { name: "freya" },
        { name: "heimdall" },
        { name: "valkyrie" },
    ];
}

export default async function AgentProfilePage({ params }: { params: Promise<{ name: string }> }) {
    const { name } = await params;
    return <AgentClient agentName={name || "thor"} />;
}
