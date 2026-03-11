"use client";

export function LoadingSkeleton({ className = "" }: { className?: string }) {
    return <div className={"skeleton " + className} />;
}

export function SkeletonCard() {
    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
                <LoadingSkeleton className="w-8 h-8 rounded-lg" />
                <LoadingSkeleton className="w-3 h-3 rounded-full" />
            </div>
            <LoadingSkeleton className="w-20 h-7 rounded mb-2" />
            <LoadingSkeleton className="w-28 h-4 rounded" />
        </div>
    );
}

export function SkeletonNodeCard() {
    return (
        <div className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
                <LoadingSkeleton className="w-10 h-10 rounded-xl" />
                <div>
                    <LoadingSkeleton className="w-20 h-5 rounded mb-1" />
                    <LoadingSkeleton className="w-16 h-3 rounded" />
                </div>
                <LoadingSkeleton className="w-3 h-3 rounded-full ml-auto" />
            </div>
            <div className="space-y-3">
                <div className="flex justify-between">
                    <LoadingSkeleton className="w-12 h-3 rounded" />
                    <LoadingSkeleton className="w-16 h-3 rounded" />
                </div>
                <div className="flex justify-between">
                    <LoadingSkeleton className="w-10 h-3 rounded" />
                    <LoadingSkeleton className="w-32 h-3 rounded" />
                </div>
                <div className="flex justify-between">
                    <LoadingSkeleton className="w-14 h-3 rounded" />
                    <LoadingSkeleton className="w-24 h-3 rounded" />
                </div>
            </div>
        </div>
    );
}

export function SkeletonChart() {
    return (
        <div className="glass-card p-5">
            <div className="flex justify-between mb-4">
                <LoadingSkeleton className="w-32 h-4 rounded" />
                <LoadingSkeleton className="w-48 h-4 rounded" />
            </div>
            <LoadingSkeleton className="w-full h-44 rounded-lg" />
        </div>
    );
}

export function SkeletonHypothesis() {
    return (
        <div className="glass-card p-5">
            <div className="flex justify-between mb-3">
                <LoadingSkeleton className="w-40 h-4 rounded" />
                <LoadingSkeleton className="w-14 h-5 rounded-full" />
            </div>
            <LoadingSkeleton className="w-full h-8 rounded mb-3" />
            <LoadingSkeleton className="w-full h-1 rounded mb-3" />
            <div className="flex justify-between">
                <LoadingSkeleton className="w-24 h-3 rounded" />
                <LoadingSkeleton className="w-16 h-6 rounded" />
            </div>
        </div>
    );
}
