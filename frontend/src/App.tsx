import React, { useEffect, useState, useCallback } from 'react';
import { Header } from './components/Header';
import { HealthCard } from './components/HealthCard';
import { FoundationRoadmap } from './components/FoundationRoadmap';
import { fetchHealth } from './api/client';
import type { HealthResponse } from './types/api';
import { ShieldCheck, Database, FileText, Cpu, Lock } from 'lucide-react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to connect to backend service.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  const isBackendHealthy = error ? false : health ? health.status === 'ok' : null;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Header isBackendHealthy={isBackendHealthy} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 sm:p-8 text-white shadow-lg">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-xs font-medium">
              <ShieldCheck className="w-4 h-4 text-indigo-400" />
              Increment 0: Foundation Layer Ready
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              India-Focused Vendor Onboarding Platform
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              &ldquo;Collect the right information once, check it consistently, explain what is
              wrong, make corrections easy, and give reviewers traceable evidence for
              decisions.&rdquo;
            </p>
          </div>
        </div>

        {/* System Health Card */}
        <HealthCard
          health={health}
          loading={loading}
          error={error}
          onRefresh={loadHealth}
        />

        {/* Foundation Architecture Highlights */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
              <Cpu className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900">FastAPI Backend</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Asynchronous Python 3.12 service with typed Pydantic schemas, CORS configuration, and modular routers.
            </p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3">
              <Database className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900">PostgreSQL & Alembic</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Relational migrations infrastructure using SQLAlchemy 2.0 with PostgreSQL drivers and local fallback support.
            </p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center mb-3">
              <Lock className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900">Private Object Storage</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Pluggable adapter interface supporting local isolated storage and Supabase S3 buckets with signed URLs.
            </p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center mb-3">
              <FileText className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900">Untrusted File Security</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Pre-upload validation guards: MIME sniffing, extension allowlist, and zero client-exposed secrets.
            </p>
          </div>
        </div>

        {/* Roadmap */}
        <FoundationRoadmap />
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div>
            Vendor Onboarding Platform &bull; Version 1.0 baseline specification
          </div>
          <div>
            Built with React 19, TypeScript, Tailwind CSS & FastAPI
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
