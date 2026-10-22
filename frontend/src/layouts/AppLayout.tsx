import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Header } from '../components/Header';
import { api } from '../services/api';
import { HealthResponse } from '../types/api';

export const AppLayout: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const location = useLocation();

  const fetchHealth = useCallback(async () => {
    setLoadingHealth(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch {
      setHealth({
        status: 'unhealthy',
        service: 'gauge-api',
        version: '0.1.0-day1',
        environment: 'offline',
        database: { connected: false, message: 'Backend unreachable' },
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    // Poll health check every 15 seconds
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const handleManualRefresh = () => {
    fetchHealth();
    setRefreshTrigger((prev) => prev + 1);
  };

  const getPageMeta = () => {
    switch (location.pathname) {
      case '/':
        return {
          title: 'Overview',
          description: 'Benchmark health, datasets, agent versions, and evaluation telemetry',
        };
      case '/datasets':
        return {
          title: 'Evaluation Datasets',
          description: 'Curated benchmark datasets and test suites for agent evaluation',
        };
      case '/versions':
        return {
          title: 'Agent Versions',
          description: 'Snapshots of agent configurations, prompt templates, and models',
        };
      case '/evaluations':
        return {
          title: 'Evaluation Runs',
          description: 'Execution history, benchmark results, and regression tracking',
        };
      case '/settings':
        return {
          title: 'Settings & Diagnostics',
          description: 'System connectivity, environment configuration, and service health',
        };
      default:
        return {
          title: 'Gauge Platform',
          description: 'AI Agent Evaluation & Benchmarking Platform',
        };
    }
  };

  const meta = getPageMeta();

  return (
    <div className="flex h-screen bg-[#0B0F17] text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <Sidebar health={health} loading={loadingHealth} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <Header
          title={meta.title}
          description={meta.description}
          health={health}
          loading={loadingHealth}
          onRefresh={handleManualRefresh}
        />

        <main className="flex-1 overflow-y-auto p-8 bg-gradient-to-b from-[#0B0F17] to-[#0D131F]">
          <Outlet context={{ refreshTrigger, health }} />
        </main>
      </div>
    </div>
  );
};
