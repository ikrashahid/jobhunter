import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function ScoreDistributionChart({ data }) {
  return (
    <div className="bg-surface border border-line rounded-card p-6">
      <h3 className="font-display font-semibold text-ink mb-1">Score distribution</h3>
      <p className="text-muted text-xs font-body mb-4">
        How final scores spread across postings considered — clustering near one
        bucket means the cross-encoder isn't discriminating well.
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2A2545" vertical={false} />
          <XAxis
            dataKey="range"
            tick={{ fill: "#9691B8", fontSize: 11 }}
            axisLine={{ stroke: "#2A2545" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#9691B8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              background: "#1F1B38",
              border: "1px solid #2A2545",
              borderRadius: 12,
              fontSize: 12,
              color: "#F3F1FB",
            }}
            cursor={{ fill: "rgba(139,150,255,0.08)" }}
          />
          <Bar dataKey="count" fill="#8B96FF" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
