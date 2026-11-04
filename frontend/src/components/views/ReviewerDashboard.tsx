import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { UserCheck, AlertTriangle, CheckCircle2, Clock, Search } from 'lucide-react';

export const ReviewerDashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-800 border border-amber-200 flex items-center justify-center">
              <UserCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Reviewer & Approver Workspace</h2>
              <p className="text-xs text-slate-500">
                Evaluation queue for <span className="font-semibold text-slate-700">{user?.organisation.name}</span> &bull;{' '}
                Human-controlled verification
              </p>
            </div>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-xs font-semibold text-amber-900">
            Audit Authority Active
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            Pending Evidence Inspection
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-2">0</div>
          <div className="text-[11px] text-slate-400 mt-1">Incoming vendor submissions</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
            Exceptions Under Investigation
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-2">0</div>
          <div className="text-[11px] text-slate-400 mt-1">Cross-check & name mismatches</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            Decisions Approved
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-2">0</div>
          <div className="text-[11px] text-slate-400 mt-1">Snapshot retained in audit log</div>
        </div>
      </div>

      {/* Reviewer Queue Table Placeholder */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Assigned Application Queue</h3>
          <span className="text-xs text-slate-400">Increment 6 Reviewer Workspace</span>
        </div>
        <div className="p-8 text-center text-slate-400 space-y-2">
          <Search className="w-8 h-8 mx-auto text-slate-300" />
          <p className="text-xs font-medium text-slate-600">
            No vendor applications currently awaiting manual review.
          </p>
          <p className="text-[11px] text-slate-400 max-w-md mx-auto">
            Once vendors submit their documents in Increment 2 and the validation engine evaluates
            them in Increments 3–4, submissions requiring human judgment will appear in this queue.
          </p>
        </div>
      </div>
    </div>
  );
};
