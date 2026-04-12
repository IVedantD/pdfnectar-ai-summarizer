import { BarChart3, Maximize2, Table2, X } from 'lucide-react';
import { memo, useMemo, useState } from 'react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, LabelList,
  Legend, Line, LineChart, Pie, PieChart,
  Tooltip as RechartsTooltip, ResponsiveContainer, XAxis, YAxis,
} from 'recharts';

/* ── Palette (4 colors only) ── */
const C = ['#6366f1', '#8b5cf6', '#06b6d4', '#64748b'];

/* ── Format numbers ── */
const fmt = (v: number) => {
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (Math.abs(v) >= 1e3) return v.toLocaleString('en-IN');
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
};

/* ── Compact tooltip ── */
const Tip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(15,23,42,0.92)', border: '1px solid #1e293b',
      borderRadius: 8, padding: '6px 10px', fontSize: 12,
      boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 2 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: '#e2e8f0', fontWeight: 600 }}>{fmt(p.value)}</div>
      ))}
    </div>
  );
};

/* ── Table view ── */
const DataTable = ({ data }: { data: any[] }) => (
  <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
    <thead>
      <tr style={{ borderBottom: '1px solid #1e293b' }}>
        <th className="text-left py-2 px-3 text-[11px] font-medium uppercase tracking-wider" style={{ color: '#64748b' }}>Category</th>
        <th className="text-right py-2 px-3 text-[11px] font-medium uppercase tracking-wider" style={{ color: '#64748b' }}>Value</th>
      </tr>
    </thead>
    <tbody>
      {data.map((d: any, i: number) => (
        <tr key={i} style={{ borderBottom: '1px solid #0f172a' }}>
          <td className="py-2 px-3 flex items-center gap-2" style={{ color: '#cbd5e1' }}>
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: C[i % C.length] }} />
            {d.name}
          </td>
          <td className="py-2 px-3 text-right font-medium tabular-nums" style={{ color: '#f1f5f9' }}>{fmt(d.value)}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

/* ── Modal ── */
const Modal = ({ children, title, onClose }: { children: React.ReactNode; title?: string; onClose: () => void }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-6" onClick={onClose}>
    <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
    <div className="relative w-full max-w-3xl rounded-2xl overflow-hidden"
      style={{ background: '#0f172a', border: '1px solid #1e293b', boxShadow: '0 24px 48px rgba(0,0,0,0.4)' }}
      onClick={e => e.stopPropagation()}>
      <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: '1px solid #1e293b' }}>
        {title && <span style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 600 }}>{title}</span>}
        <button onClick={onClose} className="p-1.5 rounded-md hover:bg-slate-800 transition-colors" style={{ color: '#64748b' }}>
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="p-4" style={{ height: 400 }}>{children}</div>
    </div>
  </div>
);

/* ═══════════ ChartRenderer ═══════════ */
const ChartRendererInner = ({ dataStr }: { dataStr: string }) => {
  const [view, setView] = useState<'chart' | 'table'>('chart');
  const [expanded, setExpanded] = useState(false);

  const parsed = useMemo(() => {
    try {
      const c = JSON.parse(dataStr);
      if (!c?.type || !Array.isArray(c?.data)) return null;
      const safe = c.data
        .filter((d: any) => d?.name && typeof d.value === 'number' && isFinite(d.value))
        .map((d: any) => ({ name: String(d.name).slice(0, 22), value: d.value }));
      if (safe.length < 2) return null;

      // Reject if all values are zero or negative
      if (safe.every((d: any) => d.value <= 0)) return null;

      // Smart chart type: if pie/donut and one slice >85%, switch to bar
      let type = c.type;
      if (type === 'pie') {
        const total = safe.reduce((s: number, d: any) => s + Math.abs(d.value), 0);
        if (total > 0 && safe.some((d: any) => Math.abs(d.value) / total > 0.85)) type = 'bar';
      }

      return { title: c.title, type, data: safe };
    } catch { return null; }
  }, [dataStr]);

  // Stable memoized data reference to prevent unnecessary re-renders
  const memoizedData = useMemo(() => parsed?.data, [parsed]);

  if (!parsed || !memoizedData) return null;
  const { title, type } = parsed;

  /* Shared config */
  const tk = { fill: '#475569', fontSize: 11 };
  const gd = { strokeDasharray: '3 3' as const, stroke: '#1e293b' };
  const tp = { content: <Tip />, cursor: { fill: 'rgba(99,102,241,0.05)' } };

  const chart = (h?: number) => {
    switch (type) {
      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={h || '100%'}>
            <PieChart>
              <Pie data={memoizedData} cx="50%" cy="50%"
                outerRadius={h ? 140 : 85} innerRadius={h ? 65 : 38}
                paddingAngle={3} dataKey="value" strokeWidth={0}
                isAnimationActive={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#475569', strokeWidth: 1 }}>
                {memoizedData.map((_: any, i: number) => <Cell key={`p${i}`} fill={C[i % C.length]} />)}
              </Pie>
              <RechartsTooltip content={<Tip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#64748b', paddingTop: 4 }} />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={h || '100%'}>
            <LineChart data={memoizedData} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
              <CartesianGrid {...gd} />
              <XAxis dataKey="name" tick={tk} axisLine={false} tickLine={false} />
              <YAxis tick={tk} axisLine={false} tickLine={false} tickFormatter={fmt} width={44} />
              <RechartsTooltip {...tp} />
              <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2.5}
                dot={{ r: 3.5, fill: '#6366f1', strokeWidth: 0 }}
                activeDot={{ r: 5, fill: '#818cf8', stroke: '#0f172a', strokeWidth: 2 }}
                isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={h || '100%'}>
            <AreaChart data={memoizedData} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
              <defs>
                <linearGradient id="af" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid {...gd} />
              <XAxis dataKey="name" tick={tk} axisLine={false} tickLine={false} />
              <YAxis tick={tk} axisLine={false} tickLine={false} tickFormatter={fmt} width={44} />
              <RechartsTooltip {...tp} />
              <Area type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} fill="url(#af)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        );

      default: // bar
        return (
          <ResponsiveContainer width="100%" height={h || '100%'}>
            <BarChart data={memoizedData} margin={{ top: 16, right: 8, bottom: 0, left: -8 }} barCategoryGap="25%">
              <CartesianGrid {...gd} />
              <XAxis dataKey="name" tick={tk} axisLine={false} tickLine={false} />
              <YAxis tick={tk} axisLine={false} tickLine={false} tickFormatter={fmt} width={44} />
              <RechartsTooltip {...tp} />
              <Bar dataKey="value" radius={[5, 5, 0, 0]} maxBarSize={44} isAnimationActive={false}>
                <LabelList dataKey="value" position="top" formatter={fmt}
                  style={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }} />
                {memoizedData.map((_: any, i: number) => <Cell key={`b${i}`} fill={C[i % C.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <>
      <div className="my-5 w-full rounded-2xl overflow-hidden transition-shadow duration-300"
        style={{
          background: 'linear-gradient(180deg, #111827 0%, #0f172a 100%)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        }}
        onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.35)')}
        onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)')}>

        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-3.5 pb-0.5">
          <div className="min-w-0 flex-1">
            {title && <h4 className="text-[13px] font-semibold truncate" style={{ color: '#e2e8f0' }}>{title}</h4>}
            <p className="text-[10px] mt-0.5" style={{ color: '#475569' }}>{memoizedData.length} data points · {type}</p>
          </div>
          <div className="flex items-center gap-0.5 ml-2">
            <button onClick={() => setView(v => v === 'chart' ? 'table' : 'chart')}
              className="p-1.5 rounded-md hover:bg-slate-800 transition-colors" style={{ color: '#64748b' }}>
              {view === 'chart' ? <Table2 className="w-3.5 h-3.5" /> : <BarChart3 className="w-3.5 h-3.5" />}
            </button>
            <button onClick={() => setExpanded(true)}
              className="p-1.5 rounded-md hover:bg-slate-800 transition-colors" style={{ color: '#64748b' }}>
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-2 pb-2.5">
          {view === 'chart' ? <div style={{ height: 240 }}>{chart()}</div> : <div className="px-1"><DataTable data={memoizedData} /></div>}
        </div>
      </div>

      {expanded && (
        <Modal title={title} onClose={() => setExpanded(false)}>
          {view === 'chart' ? chart(360) : <DataTable data={memoizedData} />}
        </Modal>
      )}
    </>
  );
};

export const ChartRenderer = memo(ChartRendererInner);
