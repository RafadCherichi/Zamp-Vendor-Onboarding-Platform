import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiResetDemo } from '../../api/client';
import { ApplicationQueue } from '../queue/ApplicationQueue';
import { ApplicationDetailsWorkspace } from '../review/ApplicationDetailsWorkspace';
import {
  ShieldCheck,
  Building2,
  Users,
  Settings,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { user, token } = useAuth();
  const [selectedApplicationId, setSelectedApplicationId] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [resetResult, setResetResult] = useState<any | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);

  const handleResetDemo = async () => {
    if (!token) return;
    if (!window.confirm('Reset demo environment? This will re-seed pristine demo accounts, 3 standard test cases, and synthetic documents.')) {
      return;
    }
    setIsResetting(true);
    setResetError(null);
    try {
      const res = await apiResetDemo(token);
      setResetResult(res);
    } catch (err: any) {
      setResetError(err?.message || 'Failed to reset demo environment.');
    } finally {
      setIsResetting(false);
    }
  };

  if (selectedApplicationId) {
    return (
      <ApplicationDetailsWorkspace
        applicationId={selectedApplicationId}
        onBack={() => setSelectedApplicationId(null)}
        onActionComplete={() => setSelectedApplicationId(null)}
        isReviewer={true}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-700 border border-purple-200 flex items-center justify-center">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Administrator Control Center</h2>
              <p className="text-xs text-slate-500">
                Governance and policy oversight for{' '}
                <span className="font-semibold text-slate-700">{user?.organisation.name}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {import.meta.env.DEV && <button
              onClick={handleResetDemo}
              disabled={isResetting}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold text-white bg-purple-600 hover:bg-purple-700 shadow-xs transition disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
              <span>{isResetting ? 'Resetting Demo...' : 'Reset & Re-Seed Demo'}</span>
            </button>}
            <div className="px-3 py-1.5 rounded-lg bg-purple-50 border border-purple-200 text-xs font-semibold text-purple-800">
              Organisation Admin
            </div>
          </div>
        </div>
      </div>

      {resetError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{resetError}</span>
        </div>
      )}

      {resetResult && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 text-xs text-emerald-900 space-y-3">
          <div className="flex items-center justify-between">
            <div className="font-bold flex items-center gap-1.5 text-emerald-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Demo Environment Reset &amp; Seeded Successfully!</span>
            </div>
            <button
              onClick={() => setResetResult(null)}
              className="text-emerald-700 hover:text-emerald-900 font-bold"
            >
              &times;
            </button>
          </div>
          <p className="text-emerald-700">
            3 repeatable demonstration cases have been restored with synthetic compliance documents, OCR findings, and verification records:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
            <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-1">
              <span className="font-bold text-slate-900 block">Case 1: Clean Application</span>
              <span className="font-mono text-[11px] text-indigo-700 font-semibold block">APP-2026-CLEAN-001</span>
              <span className="text-[11px] text-slate-500 block">Tata Industrial Supplies Pvt Ltd</span>
              <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold text-[10px] inline-block mt-1">
                Policy Gate: PASS
              </span>
            </div>
            <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-1">
              <span className="font-bold text-slate-900 block">Case 2: Correction Mismatch</span>
              <span className="font-mono text-[11px] text-indigo-700 font-semibold block">APP-2026-MISM-002</span>
              <span className="text-[11px] text-slate-500 block">Sharma Engineering Works</span>
              <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-[10px] inline-block mt-1">
                Bank Mismatch Exception
              </span>
            </div>
            <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-1">
              <span className="font-bold text-slate-900 block">Case 3: Unresolved Verification</span>
              <span className="font-mono text-[11px] text-indigo-700 font-semibold block">APP-2026-WARN-003</span>
              <span className="text-[11px] text-slate-500 block">Apex Logistics &amp; Cargo LLP</span>
              <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold text-[10px] inline-block mt-1">
                Provider Timeout &amp; Duplicate Flag
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Admin Information Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-1">
            <Building2 className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Organisation Identity</h3>
          <div className="text-xs text-slate-500 space-y-1">
            <div>
              Name: <span className="font-semibold text-slate-700">{user?.organisation.name}</span>
            </div>
            <div>
              Slug: <span className="font-mono text-slate-700">{user?.organisation.slug}</span>
            </div>
            <div>
              Data Scope: <span className="text-emerald-700 font-semibold">Strict Tenant Isolation</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center mb-1">
            <Users className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Role-Based Access Control</h3>
          <div className="text-xs text-slate-500 space-y-1">
            <div>Roles: Vendor, Procurement, Reviewer, Admin</div>
            <div>Enforcement: Backend token claims &amp; dependencies</div>
            <div>Cross-tenant queries rejected automatically</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center mb-1">
            <Settings className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Compliance &amp; Sandbox</h3>
          <div className="text-xs text-slate-500 space-y-1">
            <div>Verification Mode: Simulated Sandbox Adapters</div>
            <div>Gate Policy: Zero blocking high exceptions</div>
            <div>Masking: PAN (`AA*****4A`) &amp; Bank (`********9012`)</div>
          </div>
        </div>
      </div>

      {/* Organisation Applications Queue for Administrative Oversight */}
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div>
            <h3 className="text-base font-bold text-slate-900">Administrative Application Oversight</h3>
            <p className="text-xs text-slate-500">
              Complete view of organisational applications including escalated files, pending reviews, and reviewer assignments.
            </p>
          </div>
        </div>

        <ApplicationQueue
          onSelectApplication={(appId) => setSelectedApplicationId(appId)}
        />
      </div>
    </div>
  );
};
