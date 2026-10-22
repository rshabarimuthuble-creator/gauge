import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  loading?: boolean;
  accentColor?: 'indigo' | 'cyan' | 'emerald' | 'amber' | 'slate';
  badge?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  loading = false,
  accentColor = 'indigo',
  badge,
}) => {
  const getAccent = () => {
    switch (accentColor) {
      case 'cyan':
        return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20';
      case 'emerald':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'amber':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'slate':
        return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
      case 'indigo':
      default:
        return 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
    }
  };

  return (
    <div className="gauge-card p-5 gauge-card-hover relative overflow-hidden group">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div className={`p-2.5 rounded-lg border ${getAccent()}`}>
          {icon}
        </div>
      </div>

      <div className="mt-4 flex items-baseline justify-between">
        {loading ? (
          <div className="h-8 w-24 bg-slate-800 animate-pulse rounded-md"></div>
        ) : (
          <div className="text-3xl font-bold tracking-tight text-white font-mono">
            {value}
          </div>
        )}
        {badge && <div>{badge}</div>}
      </div>

      {subtitle && (
        <p className="mt-2 text-xs text-slate-400 flex items-center gap-1">
          {subtitle}
        </p>
      )}

      {/* Subtle bottom edge glow */}
      <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-slate-700 group-hover:via-indigo-500/50 to-transparent transition-all duration-300" />
    </div>
  );
};
