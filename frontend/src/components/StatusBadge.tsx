import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, XCircle, Activity, Database } from 'lucide-react';

interface StatusBadgeProps {
  status: 'ok' | 'degraded' | 'unhealthy' | 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'sm',
  showIcon = true,
}) => {
  const normalized = status.toLowerCase();

  const getStyle = () => {
    switch (normalized) {
      case 'ok':
      case 'completed':
      case 'healthy':
        return {
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          icon: <CheckCircle2 className="w-3.5 h-3.5" />,
          label: normalized === 'ok' ? 'Healthy' : 'Completed',
        };
      case 'running':
        return {
          bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
          icon: <Activity className="w-3.5 h-3.5 animate-pulse" />,
          label: 'Running',
        };
      case 'pending':
      case 'degraded':
        return {
          bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          icon: <AlertTriangle className="w-3.5 h-3.5" />,
          label: normalized === 'degraded' ? 'Degraded' : 'Pending',
        };
      case 'failed':
      case 'unhealthy':
      case 'error':
        return {
          bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
          icon: <XCircle className="w-3.5 h-3.5" />,
          label: normalized === 'unhealthy' ? 'Unhealthy' : 'Failed',
        };
      case 'cancelled':
        return {
          bg: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
          icon: <Clock className="w-3.5 h-3.5" />,
          label: 'Cancelled',
        };
      default:
        return {
          bg: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
          icon: <Database className="w-3.5 h-3.5" />,
          label: status,
        };
    }
  };

  const { bg, icon, label } = getStyle();
  const sizeClasses = size === 'sm' ? 'text-xs px-2.5 py-0.5' : 'text-sm px-3 py-1';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium border ${bg} ${sizeClasses}`}>
      {showIcon && icon}
      <span className="capitalize">{label}</span>
    </span>
  );
};
