import React from 'react';
import { RiskLevel, NodeCategory } from '../../types/graph';

interface RiskBadgeProps {
  level: RiskLevel;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md', showDot = true }) => {
  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5 tracking-wider font-semibold',
    md: 'text-xs px-2.5 py-1 tracking-wider font-semibold',
    lg: 'text-sm px-3 py-1.5 tracking-wider font-bold',
  }[size];

  const levelStyles: Record<RiskLevel, { bg: string; text: string; border: string; dot: string }> = {
    critical: {
      bg: 'bg-rose-500/10 dark:bg-rose-500/15',
      text: 'text-rose-600 dark:text-rose-400',
      border: 'border-rose-500/30 dark:border-rose-500/40',
      dot: 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]',
    },
    high: {
      bg: 'bg-orange-500/10 dark:bg-orange-500/15',
      text: 'text-orange-600 dark:text-orange-400',
      border: 'border-orange-500/30 dark:border-orange-500/40',
      dot: 'bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.6)]',
    },
    medium: {
      bg: 'bg-amber-500/10 dark:bg-amber-500/15',
      text: 'text-amber-600 dark:text-amber-400',
      border: 'border-amber-500/30 dark:border-amber-500/40',
      dot: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]',
    },
    low: {
      bg: 'bg-emerald-500/10 dark:bg-emerald-500/15',
      text: 'text-emerald-600 dark:text-emerald-400',
      border: 'border-emerald-500/30 dark:border-emerald-500/40',
      dot: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]',
    },
  };

  const style = levelStyles[level] || levelStyles.low;

  return (
    <span
      className={`inline-flex items-center gap-1.5 uppercase rounded-md border ${style.bg} ${style.text} ${style.border} ${sizeClasses}`}
    >
      {showDot && <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${style.dot}`} />}
      {level}
    </span>
  );
};

interface CategoryBadgeProps {
  category: NodeCategory;
  size?: 'sm' | 'md';
}

export const CategoryBadge: React.FC<CategoryBadgeProps> = ({ category, size = 'md' }) => {
  const sizeClasses = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5';

  const categoryStyles: Record<NodeCategory, { bg: string; text: string; border: string }> = {
    ACTOR: {
      bg: 'bg-cyan-500/10 dark:bg-cyan-500/15',
      text: 'text-cyan-600 dark:text-cyan-300',
      border: 'border-cyan-500/30 dark:border-cyan-500/40',
    },
    HANDLE: {
      bg: 'bg-indigo-500/10 dark:bg-indigo-500/15',
      text: 'text-indigo-600 dark:text-indigo-300',
      border: 'border-indigo-500/30 dark:border-indigo-500/40',
    },
    WALLET: {
      bg: 'bg-emerald-500/10 dark:bg-emerald-500/15',
      text: 'text-emerald-600 dark:text-emerald-300',
      border: 'border-emerald-500/30 dark:border-emerald-500/40',
    },
  };

  const style = categoryStyles[category];

  return (
    <span
      className={`inline-flex items-center font-mono-code font-medium uppercase tracking-wider rounded border ${style.bg} ${style.text} ${style.border} ${sizeClasses}`}
    >
      {category}
    </span>
  );
};

export const ConfidenceScore: React.FC<{ value: number; size?: 'sm' | 'md' | 'lg' }> = ({
  value,
  size = 'md',
}) => {
  const percentage = Math.round(value * 100);
  const sizeClass = {
    sm: 'text-xs',
    md: 'text-sm font-semibold',
    lg: 'text-lg font-bold',
  }[size];

  const getColor = (p: number) => {
    if (p >= 85) return 'text-cyan-600 dark:text-cyan-400';
    if (p >= 70) return 'text-indigo-600 dark:text-indigo-400';
    return 'text-amber-600 dark:text-amber-400';
  };

  return (
    <span className={`font-mono-code ${getColor(percentage)} ${sizeClass}`}>
      {percentage}%
    </span>
  );
};
