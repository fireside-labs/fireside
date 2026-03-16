"use client";

import { PredictionScore } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";

interface Props {
    data: PredictionScore[];
}

export default function PredictionChart({ data }: Props) {
    const avgAccuracy = data.length > 0
        ? Math.round((data.reduce((sum, d) => sum + d.accuracy, 0) / data.length) * 100)
        : 0;

    const totalPredictions = data.reduce((sum, d) => sum + d.total_predictions, 0);
    const totalSurprises = data.reduce((sum, d) => sum + d.surprise_events, 0);

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold text-sm">🔮 Prediction Accuracy</h3>
                <div className="flex gap-4 text-xs">
                    <span className="text-[var(--color-rune-dim)]">
                        Avg: <span className="text-[var(--color-neon)] font-mono">{avgAccuracy}%</span>
                    </span>
                    <span className="text-[var(--color-rune-dim)]">
                        Total: <span className="text-white font-mono">{totalPredictions}</span>
                    </span>
                    <span className="text-[var(--color-rune-dim)]">
                        Surprises: <span className="text-[var(--color-warning)] font-mono">{totalSurprises}</span>
                    </span>
                </div>
            </div>

            <div style={{ width: "100%", height: 180 }}>
                <ResponsiveContainer>
                    <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
                        <defs>
                            <linearGradient id="neonGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis
                            dataKey="timestamp"
                            tick={{ fill: "#6a6a80", fontSize: 11 }}
                            axisLine={{ stroke: "#1a1a2e" }}
                            tickLine={false}
                        />
                        <YAxis
                            domain={[0.4, 1]}
                            tick={{ fill: "#6a6a80", fontSize: 11 }}
                            axisLine={{ stroke: "#1a1a2e" }}
                            tickLine={false}
                            tickFormatter={(v: number) => Math.round(v * 100) + "%"}
                        />
                        <Tooltip
                            contentStyle={{
                                background: "#12121a",
                                border: "1px solid rgba(255,255,255,0.08)",
                                borderRadius: "8px",
                                fontSize: "12px",
                                color: "#a0a0b8",
                            }}
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            formatter={((value: any) => [Math.round(Number(value || 0) * 100) + "%", "Accuracy"]) as any}
                            labelStyle={{ color: "#ffffff" }}
                        />
                        <Area
                            type="monotone"
                            dataKey="accuracy"
                            stroke="#F59E0B"
                            strokeWidth={2}
                            fill="url(#neonGradient)"
                            dot={{ fill: "#F59E0B", r: 3, strokeWidth: 0 }}
                            activeDot={{ r: 5, fill: "#F59E0B", stroke: "#0a0a0f", strokeWidth: 2 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
