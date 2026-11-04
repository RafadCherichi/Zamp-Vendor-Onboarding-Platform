import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiFetchCurrentApplication } from '../../api/applications';
import type { Application } from '../../types/application';
import { OnboardingWizard } from '../vendor/OnboardingWizard';
import { SubmissionConfirmation } from '../vendor/SubmissionConfirmation';
import { RefreshCw, ShieldAlert } from 'lucide-react';

export const VendorDashboard: React.FC = () => {
  const { token } = useAuth();
  const [application, setApplication] = useState<Application | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadApplication = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetchCurrentApplication(token);
      setApplication(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to initialize vendor application.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadApplication();
  }, [loadApplication]);

  if (loading) {
    return (
      <div className="py-16 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-indigo-600" />
        Loading your onboarding profile & document checklist...
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center max-w-lg mx-auto shadow-2xs space-y-4">
        <div className="p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-200 text-xs flex items-center gap-2 text-left">
          <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{error || 'Unable to retrieve application profile.'}</span>
        </div>
        <button
          onClick={loadApplication}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  if (['SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'ESCALATED'].includes(application.status)) {
    return <SubmissionConfirmation application={application} />;
  }

  return (
    <OnboardingWizard
      token={token!}
      initialApplication={application}
      onRefresh={loadApplication}
      onSubmitSuccess={() => {
        loadApplication();
      }}
    />
  );
};
