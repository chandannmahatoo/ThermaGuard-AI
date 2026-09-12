'use client';
import React from 'react';

export type RiskLevel = 'Critical' | 'High' | 'Medium' | 'Normal' | string;
export type ProviderHealthState = 'healthy' | 'configured' | 'disabled' | 'not_configured' | 'degraded' | 'failed' | string;
export type SystemReadinessState = 'REAL' | 'DEMO' | 'UNAVAILABLE' | 'BLOCKED' | 'FALLBACK';

export function RiskBadge({ level }: { level: RiskLevel | undefined | null }) {
  const norm = (level || 'Normal').toLowerCase();
  return <span className={`badge ${norm}`}>{level || 'Unknown'}</span>;
}

export function StatusBadge({ state }: { state: SystemReadinessState }) {
  return <span className={`status-badge ${(state || 'UNAVAILABLE').toLowerCase()}`}>{state}</span>;
}

export function ProviderBadge({ state }: { state: ProviderHealthState }) {
  const stateLabels: Record<string, string> = {
    healthy: 'Healthy',
    configured: 'Configured',
    disabled: 'Disabled',
    not_configured: 'Not configured',
    degraded: 'Degraded',
    failed: 'Failed',
  };
  const label = stateLabels[state] || state;
  return <span className={`provider-state provider-${state}`}>{label}</span>;
}
