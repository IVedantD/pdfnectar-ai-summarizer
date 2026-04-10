import { BarChart3, Maximize2, Table2, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  XAxis, YAxis,
} from 'recharts';

/* ──── Minimal 4-color palette ──── */
const COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#64748b'];

/* ──── Number Formatter ──── */
const fmt = (v: number): string => {
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (Math.abs(v) >= 1e3) return v.toLocaleString('en-IN');
  if (Number.isInteger(v)) return v.toString();
  return v.toFixed(2);
};

/* ──── Compact Tooltip ──── */
const Tip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#1e293b',
      border: '1px solid #334155',
      borderRadius: 8,
      padding: '6px 10px',
      fontSize: 12,
      lineHeight: '18px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
    }}>
      <span style={{ color: '#94a3b8' }}>{label}</span>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: '#f1f5f9', fontWeight: 600 }}>{fmt(p.value)}</div>
      ))}
    </div>
  );
};

/* ──── Table View ──── */
const DataTable = ({ data }: { data: any[] }) => (
  <div className="w-full overflow-x-auto">
    <table className="w-full text-sm">
      <thead>
        <tr style={{ borderBottom: '1px solid #1e293b' }}>
          <th className="text-left py-2.5 px-3 text-[11px] font-medium uppercase tracking-wider" style={{ color: '#64748b' }}>Category</th>
          <th className="text-right py-2.5 px-3 text-[11px] font-medium uppercase tracking-wider" style={{ color: '#64748b' }}>Value</th>
        </tr>
      </thead>
      <tbody>
        {data.map((item: any, i: number) => (
          <tr key={i} style={{ borderBottom: '1px solid #0f172a' }} className="transition-colors hover:bg-white/[0.03]">
            <td className="py-2.5 px-3 flex items-center gap-2" style={{ color: '#cbd5e1' }}>
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
              {item.name}
            </td>
            <td className="py-2.5 px-3 text-right font-medium tabular-nums" style={{ color: '#f1f5f9' }}>{fmt(item.value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

/* ──── Modal ──── */
const Modal = ({ children, title, onClose }: { children: React.ReactNode; title?: string; onClose: () => void }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-6" onClick={onClose}>
    <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
    <div
      className="relative w-full max-w-3xl rounded-xl overflow-hidden"
      style={{ background: '#0f172a', border: '1px solid #1e293b', boxShadow: '0 24px 48px rgba(0,0,0,0.4)' }}
      onClick={e => e.stopPropagation()}
    >
      <div className="flex items-center justify-between px-5 py-3.5" style={{ borderBottom: '1px solid #1e293b' }}>
        {title && <h3 style={{ color: '#f1f5f9', fontSize: 15, fontWeight: 600 }}>{title}</h3>}
        <button onClick={onClose} className="p-1.5 rounded-md transition-colors" style={{ color: '#64748b' }}
          onMouseEnter={e => (e.currentTarget.style.background = '#1e293b')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="p-5" style={{ height: 420 }}>{children}</div>
    </div>
  </div>
);

/* ─────── Main Component ─────── */
export const ChartRenderer = ({ dataStr }: { dataStr: string }) => {
  const [view, setView] = useState<'chart' | 'table'>('chart');
  const [expanded, setExpanded] = useState(false);

  const parsed = useMemo(() => {
    try {
      const c = JSON.parse(dataStr);
      if (!c?.type || !Array.isArray(c?.data)) return null;
      const safe = c.data
        .filter((d: any) => d?.name && typeof d.value === 'number' && isFinite(d.value))
        .map((d: any) => ({ ...d, name: String(d.name).length > 22 ? String(d.name).slice(0, 20) + '…' : String(d.name) }));
      return safe.length >= 2 ? { ...c, data: safe } : null;
    } catch { return null; }
  }, [dataStr]);

  if (!parsed) return null;
  const { data, type, title } = parsed;

  /* Shared props */
  const tick = { fill: '#475569', fontSize: 11 };
  const grid = { strokeDasharray: '3 3', stroke: '#1e293b' };
  const anim = { animationDuration: 500, animationEasing: 'ease-out' as const };
  const tip = { content: <Tip />, cursor: { fill: 'rgba(99,102,241,0.06)' } };

  const chart = (h?: number) => {
    switch (type) {
      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={h || '100%'}>
            <PieChart>
              <Pie data={data} cx="50%" cy="50%" outerRadius={h ? 150 : 88} innerRadius={h ? 70 : 40}
                paddingAngle={3} dataKey="value" strokeWidth={0}
                labelLine={{ stroke: '#475569', strokeWidth: 1 }}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                {...anim}>
                {data.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <RechartsTooltip content={<Tip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#64748b', paddingTop: 4 }} />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={h || '100%'}>
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid {...grid} />
              <XAxis dataKey="name" tick={tick} axisLine={false} tickLine={false} />
              <YAxis tick={tick} axisLine={false} tickLine={false} tickFormatter={fmt} width={40} />
              <RechartsTooltip {...tip} />
              <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2.5}
                dot={{ r: 4, fill: '#6366f1', strokeWidth: 0 }}
                activeDot={{ r: 6, fill: '#818cf8', stroke: '#0f172a', strokeWidth: 2 }}
                {...anim} />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={h || '100%'}>
            <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="aFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid {...grid} />
              <XAxis dataKey="name" tick={tick} axisLine={false} tickLine={false} />
              <YAxis tick={tick} axisLine={false} tickLine={false} tickFormatter={fmt} width={40} />
              <RechartsTooltip {...tip} />
              <Area type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} fill="url(#aFill)" {...anim} />
            </AreaChart>
          </ResponsiveContainer>
        );

      default: // bar
        return (
          <ResponsiveContainer width="100%" height={h || '100%'}>
            <BarChart data={data} margin={{ top: 16, right: 12, bottom: 0, left: 0 }} barCategoryGap="25%">
              <CartesianGrid {...grid} />
              <XAxis dataKey="name" tick={tick} axisLine={false} tickLine={false} />
              <YAxis tick={tick} axisLine={false} tickLine={false} tickFormatter={fmt} width={40} />
              <RechartsTooltip {...tip} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={48} {...anim}>
                <LabelList dataKey="value" position="top" formatter={fmt}
                  style={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }} />
                {data.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );
    }
  };

  const cardBg = '#111827';
  const borderColor = '#1e293b';

  return (
    <>
      {/* Card */}
      <div
        className="my-6 w-full rounded-2xl overflow-hidden transition-shadow duration-300 cursor-default"
        style={{
          background: cardBg,
          border: `1px solid ${borderColor}`,
          boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
        }}
        onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.3)')}
        onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.2)')}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-4 pb-1">
          <div className="min-w-0 flex-1">
            {title && <h4 className="text-sm font-semibold truncate" style={{ color: '#f1f5f9' }}>{title}</h4>}
            <p className="text-[11px] mt-0.5" style={{ color: '#475569' }}>{data.length} data points · {type} chart</p>
          </div>
          <div className="flex items-center gap-0.5 ml-2">
            <button onClick={() => setView(v => v === 'chart' ? 'table' : 'chart')}
              className="p-1.5 rounded-md transition-colors" style={{ color: '#64748b' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#1e293b')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              title={view === 'chart' ? 'Table view' : 'Chart view'}>
              {view === 'chart' ? <Table2 className="w-3.5 h-3.5" /> : <BarChart3 className="w-3.5 h-3.5" />}
            </button>
            <button onClick={() => setExpanded(true)}
              className="p-1.5 rounded-md transition-colors" style={{ color: '#64748b' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#1e293b')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              title="Expand">
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-3 pb-3">
          {view === 'chart' ? (
            <div style={{ height: 260 }}>{chart()}</div>
          ) : (
            <DataTable data={data} />
          )}
        </div>
      </div>

      {/* Modal */}
      {expanded && (
        <Modal title={title} onClose={() => setExpanded(false)}>
          {view === 'chart' ? chart(380) : <DataTable data={data} />}
        </Modal>
      )}
    </>
  );
};
