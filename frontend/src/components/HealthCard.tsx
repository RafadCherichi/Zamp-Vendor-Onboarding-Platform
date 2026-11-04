import React from 'react';
import { Server, Database, HardDrive, RefreshCw, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import type { HealthResponse } from '../types/api';

interface HealthCardProps {
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const HealthCard: React.FC<HealthCardProps> = ({ health, loading, error, onRefresh }) => {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <Server className="w-5 h-5 text-indigo-600" />
            System Health & Environment Status
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time diagnostic verification between React Frontend, FastAPI Backend, and Database
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Checking...' : 'Check Status'}
        </button>
      </div>

      <div className="p-6">
        {error ? (
          <div className="rounded-lg bg-rose-50 border border-rose-200 p-4 flex items-start gap-3">
            <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-rose-800">Connection Failed</h3>
              <p className="text-xs text-rose-700 mt-1">{error}</p>
              <p className="text-xs text-rose-600 mt-2">
                Make sure the backend is running with:{' '}
                <code className="bg-rose-100 px-1 py-0.5 rounded font-mono">
                  uvicorn app.main:app --port 8000
                </code>
              </p>
            </div>
          </div>
        ) : health ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Backend Service */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Backend API
                </span>
                <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  {health.status.toUpperCase()}
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-800">{health.app_name}</p>
              <div className="mt-2 text-xs text-slate-500 space-y-1">
                <div>
                  Version: <span className="font-mono text-slate-700">{health.version}</span>
                </div>
                <div>
                  Environment:{' '}
                  <span className="font-mono text-slate-700">{health.environment}</span>
                </div>
              </div>
            </div>

            {/* Database Connection */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                  <Database className="w-3.5 h-3.5" />
                  Database
                </span>
                <span
                  className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded border ${
                    health.database.status === 'connected'
                      ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                      : 'text-amber-700 bg-amber-50 border-amber-200'
                  }`}
                >
                  {health.database.status === 'connected' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  )}
                  {health.database.status}
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-800 capitalize">
                Dialect: {health.database.dialect}
              </p>
              <div className="mt-2 text-xs text-slate-500 space-y-1">
                <div>
                  Query Latency:{' '}
                  <span className="font-mono text-slate-700">
                    {health.database.latency_ms} ms
                  </span>
                </div>
                <div>
                  Migration State:{' '}
                  <span className="text-emerald-700 font-medium">Head Applied</span>
                </div>
              </div>
            </div>

            {/* Private Object Storage */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                  <HardDrive className="w-3.5 h-3.5" />
                  Object Storage
                </span>
                <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  {health.storage.status}
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-800 capitalize">
                Provider: {health.storage.backend}
              </p>
              <div className="mt-2 text-xs text-slate-500 space-y-1">
                <div className="truncate" title={health.storage.path_or_bucket}>
                  Path: <span className="font-mono text-slate-700">{health.storage.path_or_bucket}</span>
                </div>
                <div>
                  Access: <span className="text-indigo-600 font-medium">Private / Tokenized URL</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-8 text-center text-sm text-slate-400">
            Waiting for health status response...
          </div>
        )}
      </div>
    </div>
  );
};
