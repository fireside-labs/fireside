import PipelineClient from "./PipelineClient";

export function generateStaticParams() {
    return [{ id: "placeholder" }];
}

export default async function PipelineDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return <PipelineClient id={id} />;
}
