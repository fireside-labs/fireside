import MarketplaceClient from "./MarketplaceClient";

export function generateStaticParams() {
    return [{ id: "placeholder" }];
}

export default async function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return <MarketplaceClient id={id} />;
}
