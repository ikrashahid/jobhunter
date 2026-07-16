import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";

const COLORS = ["#8B96FF", "#5FE0AE", "#FFD166", "#FF8A72", "#C792EA"];

export default function SourceBreakdownChart({ data }) {
  return (
    <div className="bg-surface border border-line rounded-card p-6">
      <h3 className="font-display font-semibold text-ink mb-1">Postings by source</h3>
      <p className="text-muted text-xs font-body mb-4">
        Which fetcher is actually pulling weight — tells you whether to invest more in one source.
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2A2545" horizontal={false} />
          <XAxis type="number" tick={{ fill: "#9691B8", fontSize: 11 }} axisLine={{ stroke: "#2A2545" }} tickLine={false} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="source"
            tick={{ fill: "#F3F1FB", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={80}
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
          <Bar dataKey="count" radius={[0, 6, 6, 0]}>
            {data.map((entry, i) => (
              <Cell key={entry.source} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
