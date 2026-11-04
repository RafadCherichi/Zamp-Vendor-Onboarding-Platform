import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { ShieldCheck, Building2, Users, Settings } from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { user } = useAuth();

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
                Governance, membership roles, and validation policies for{' '}
                <span className="font-semibold text-slate-700">{user?.organisation.name}</span>
              </p>
            </div>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-purple-50 border border-purple-200 text-xs font-semibold text-purple-800">
            Organisation Admin
          </div>
        </div>
      </div>

      {/* Admin Cards */}
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
              Data Scope: <span className="text-emerald-700 font-semibold">Isolated Workspace</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center mb-1">
            <Users className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Role-Based Access Control</h3>
          <div className="text-xs text-slate-500 space-y-1">
            <div>Supported Roles: 4 (Vendor, Procurement, Reviewer, Admin)</div>
            <div>Enforcement: Backend middleware on every endpoint</div>
            <div>Multi-tenancy: Organisation-scoped tables & foreign keys</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center mb-1">
            <Settings className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Policy & Document Rules</h3>
          <div className="text-xs text-slate-500 space-y-1">
            <div>Policy Baseline Version: 1.0.0</div>
            <div>Verification Mode: Simulated / Mock Adapters (Demo)</div>
            <div>Storage Mode: Private Isolated Adapter</div>
          </div>
        </div>
      </div>
    </div>
  );
};
