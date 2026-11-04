import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { Building2, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const VendorDashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-2xs">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center justify-center">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Vendor Portal</h2>
            <p className="text-xs text-slate-500">
              Welcome, <span className="font-semibold text-slate-700">{user?.full_name}</span> &bull;{' '}
              <span className="font-mono">{user?.email}</span>
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-200 text-xs text-emerald-800 space-y-1">
          <div className="font-bold flex items-center gap-1.5 text-emerald-900">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            Invitation Verified &bull; Scoped to {user?.organisation.name}
          </div>
          <p>
            Your vendor identity is verified and scoped to buyer organisation{' '}
            <span className="font-semibold">{user?.organisation.name}</span>. You can only view and
            manage your own submissions.
          </p>
        </div>
      </div>

      {/* Onboarding Flow Preview */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs space-y-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Next Step: Onboarding Form (Increment 2)</h3>
          <p className="text-xs text-slate-500 mt-1">
            As per the implementation roadmap, Increment 2 will enable the 6-section dynamic vendor
            form and activity-based conditional document checklist:
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider">
              1. Business Identity
            </span>
            <p className="text-xs text-slate-600 mt-1">
              Legal entity details, constitution (Proprietorship, Partnership, LLP, Company), and addresses.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider">
              2. Tax & Bank Verification
            </span>
            <p className="text-xs text-slate-600 mt-1">
              PAN, GSTIN, IFSC, Account confirmation, and cancelled cheque evidence.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider">
              3. Conditional Documents
            </span>
            <p className="text-xs text-slate-600 mt-1">
              Policy-driven checklists based on constitution and business activity.
            </p>
          </div>
        </div>
      </div>

      {/* Privacy Notice */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-700">Data Isolation & Security:</span> Your data
          is encrypted at rest and in transit. Bank and tax credentials will be masked in shared views,
          and documents are stored in private object storage.
        </div>
      </div>
    </div>
  );
};
