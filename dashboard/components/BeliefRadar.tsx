"use client";

import type { BeliefShadow } from "@/lib/api";

export default function BeliefRadar({ shadows }: { shadows: BeliefShadow[] }) {
    const size = 200;
    const cx = size / 2;
    const cy = size / 2;
    const maxR = 80;
    const nodeColors = ["var(--color-neon)", "var(--color-info)", "var(--color-warning)"];

    // Get dimension labels from first shadow
    const dims = shadows[0]?.dimensions || [];
    const angleStep = (2 * Math.PI) / dims.length;

    function polarToXY(angle: number, radius: number) {
        return {
            x: cx + radius * Math.cos(angle - Math.PI / 2),
            y: cy + radius * Math.sin(angle - Math.PI / 2),
        };
    }

    // Grid rings
    const rings = [0.25, 0.5, 0.75, 1.0];

    return (
        <div className="glass-card p-5">
            <h3 className="text-white font-semibold mb-3">🌐 Belief Shadows</h3>
            <p className="text-xs text-[var(--color-rune-dim)] mb-4">Confidence vs. accuracy per node</p>

            <div className="flex justify-center">
                <svg width={size} height={size} className="overflow-visible">
                    {/* Grid rings */}
                    {rings.map((r) => (
                        <circle
                            key={r}
                            cx={cx}
                            cy={cy}
                            r={maxR * r}
                            fill="none"
                            stroke="var(--color-glass-border)"
                            strokeWidth="0.5"
                        />
                    ))}

                    {/* Axis lines + labels */}
                    {dims.map((d, i) => {
                        const angle = i * angleStep;
                        const end = polarToXY(angle, maxR + 4);
                        const label = polarToXY(angle, maxR + 18);
                        return (
                            <g key={d.label}>
                                <line x1={cx} y1={cy} x2={end.x} y2={end.y} stroke="var(--color-glass-border)" strokeWidth="0.5" />
                                <text
                                    x={label.x}
                                    y={label.y}
                                    textAnchor="middle"
                                    dominantBaseline="middle"
                                    fill="var(--color-rune-dim)"
                                    fontSize="9"
                                >
                                    {d.label}
                                </text>
                            </g>
                        );
                    })}

                    {/* Data polygons */}
                    {shadows.map((shadow, si) => {
                        const confPoints = shadow.dimensions.map((d, i) => {
                            const p = polarToXY(i * angleStep, d.confidence * maxR);
                            return `${p.x},${p.y}`;
                        }).join(" ");

                        const accPoints = shadow.dimensions.map((d, i) => {
                            const p = polarToXY(i * angleStep, d.accuracy * maxR);
                            return `${p.x},${p.y}`;
                        }).join(" ");

                        const color = nodeColors[si % nodeColors.length];

                        return (
                            <g key={shadow.node}>
                                {/* Confidence polygon (solid) */}
                                <polygon
                                    points={confPoints}
                                    fill={color}
                                    fillOpacity={0.1}
                                    stroke={color}
                                    strokeWidth="1.5"
                                />
                                {/* Accuracy polygon (dashed) */}
                                <polygon
                                    points={accPoints}
                                    fill="none"
                                    stroke={color}
                                    strokeWidth="1"
                                    strokeDasharray="3 3"
                                    opacity={0.6}
                                />
                            </g>
                        );
                    })}
                </svg>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap justify-center gap-4 mt-3">
                {shadows.map((s, i) => (
                    <div key={s.node} className="flex items-center gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ background: nodeColors[i % nodeColors.length] }} />
                        <span className="text-xs text-white font-medium">{s.node}</span>
                        {s.gap_score > 0.1 && (
                            <span className="text-[10px] text-[var(--color-danger)]">gap: {(s.gap_score * 100).toFixed(0)}%</span>
                        )}
                    </div>
                ))}
            </div>
            <p className="text-center text-[10px] text-[var(--color-rune-dim)] mt-1">
                Solid = confidence · Dashed = accuracy
            </p>
        </div>
    );
}
