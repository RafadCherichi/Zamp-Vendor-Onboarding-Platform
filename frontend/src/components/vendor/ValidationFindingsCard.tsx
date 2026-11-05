import React, { useState, useEffect } from 'react';
import type { ValidationRun } from '../../types/validation';
import { apiFetchValidation, apiTriggerValidation } from '../../api/validation';

interface ValidationFindingsCardProps {
  token: string;
  applicationId: string;
  isReviewerView?: boolean;
}

export const ValidationFindingsCard: React.FC<ValidationFindingsCardProps> = ({
  token,
  applicationId,
}) => {
  const [validationRun, setValidationRun] = useState<ValidationRun | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [validating, setValidating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeLayer, setActiveLayer] = useState<string>('ALL');

  const loadValidation = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetchValidation(token, applicationId);
      setValidationRun(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load validation findings');
    } finally {
      setLoading(false);
    }
  };

  const handleRevalidate = async () => {
    try {
      setValidating(true);
      setError(null);
      const res = await apiTriggerValidation(token, applicationId, 'FULL', 'User requested full revalidation');
      setValidationRun(res);
    } catch (err: any) {
      setError(err.message || 'Validation execution failed');
    } finally {
      setValidating(false);
    }
  };

  useEffect(() => {
    if (applicationId && token) {
      loadValidation();
    }
  }, [applicationId, token]);

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center space-x-3">
          <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium text-slate-600">Running deterministic validation checks...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-xl border border-red-200 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-red-700">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-semibold">{error}</span>
          </div>
          <button
            onClick={loadValidation}
            className="text-xs font-semibold px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-800 rounded-md transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!validationRun) {
    return null;
  }

  const findings = validationRun.findings || [];

  const isIdentityTax = (f: any) => {
    const id = (f.check_id || '').toUpperCase();
    const name = (f.check_name || '').toLowerCase();
    return (
      id.includes('PAN') ||
      id.includes('GST') ||
      id.includes('UDYAM') ||
      id.includes('CIN') ||
      id.includes('LLPIN') ||
      name.includes('pan') ||
      name.includes('gst') ||
      name.includes('tax') ||
      name.includes('msme') ||
      name.includes('identity') ||
      name.includes('constitution') ||
      name.includes('company')
    );
  };

  const isBanking = (f: any) => {
    const id = (f.check_id || '').toUpperCase();
    const name = (f.check_name || '').toLowerCase();
    return (
      id.includes('IFSC') ||
      id.includes('BANK') ||
      id.includes('ACCOUNT') ||
      name.includes('bank') ||
      name.includes('ifsc') ||
      name.includes('beneficiary')
    );
  };

  const isDocOrCross = (f: any) => {
    return !isIdentityTax(f) && !isBanking(f);
  };

  const identityTaxCount = findings.filter(isIdentityTax).length;
  const bankingCount = findings.filter(isBanking).length;
  const docMatchingCount = findings.filter(isDocOrCross).length;
  const attentionCount = findings.filter((f) => f.status === 'FAILED' || f.status === 'WARNING').length;

  const filteredFindings = findings.filter((f) => {
    if (activeLayer === 'ALL') return true;
    if (activeLayer === 'IDENTITY_TAX') return isIdentityTax(f);
    if (activeLayer === 'BANKING') return isBanking(f);
    if (activeLayer === 'DOCUMENTS') return isDocOrCross(f);
    if (activeLayer === 'ATTENTION') return f.status === 'FAILED' || f.status === 'WARNING';
    return true;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            Passed
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            Needs Attention
          </span>
        );
      case 'WARNING':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            Notice
          </span>
        );
      case 'UNAVAILABLE':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-100 text-sky-800 border border-sky-200">
            Manual Review Needed
          </span>
        );
      case 'UNVERIFIED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
            Pending Check
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  const getSeverityBadge = (status: string, sev: string) => {
    // Only display severity badges for non-passed actionable items
    if (status === 'PASSED' || status === 'UNAVAILABLE' || status === 'UNVERIFIED') {
      return null;
    }
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
            Action Required
          </span>
        );
      case 'HIGH':
        return (
          <span className="text-[10px] font-bold text-orange-700 uppercase tracking-wider bg-orange-50 px-2 py-0.5 rounded border border-orange-200">
            Important
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
            Review
          </span>
        );
      case 'LOW':
        return (
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
            Optional
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header Banner */}
      <div className="p-5 border-b border-slate-200 bg-slate-50/70">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">Application Verification Summary</h3>
            <p className="text-xs text-slate-600 mt-1">
              We automatically verify your business information and documents against statutory formats and registries to speed up approval.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleRevalidate}
              disabled={validating}
              className="inline-flex items-center px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white text-xs font-semibold rounded-lg shadow-sm transition"
            >
              {validating ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin mr-1.5" />
                  Checking...
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Revalidate Checks
                </>
              )}
            </button>
          </div>
        </div>

        {/* Counter Summary Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 mt-4">
          <div className="bg-white p-2.5 rounded-lg border border-emerald-200 flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-800">Passed</span>
            <span className="text-sm font-bold text-emerald-700">{validationRun.passed_count}</span>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-rose-200 flex items-center justify-between">
            <span className="text-xs font-semibold text-rose-800">Needs Attention</span>
            <span className="text-sm font-bold text-rose-700">{validationRun.failed_count}</span>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-amber-200 flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-800">Notices</span>
            <span className="text-sm font-bold text-amber-700">{validationRun.warning_count}</span>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-sky-200 flex items-center justify-between">
            <span className="text-xs font-semibold text-sky-800">Manual Review</span>
            <span className="text-sm font-bold text-sky-700">{validationRun.unavailable_count}</span>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-purple-200 flex items-center justify-between">
            <span className="text-xs font-semibold text-purple-800">Pending</span>
            <span className="text-sm font-bold text-purple-700">{validationRun.unverified_count}</span>
          </div>
        </div>
      </div>

      {/* Business-Friendly Filter Tabs */}
      <div className="flex border-b border-slate-200 bg-slate-50/50 px-4 gap-2 text-xs font-medium overflow-x-auto">
        <button
          onClick={() => setActiveLayer('ALL')}
          className={`py-2.5 px-3 border-b-2 font-semibold transition whitespace-nowrap ${
            activeLayer === 'ALL'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          All Checks ({findings.length})
        </button>
        <button
          onClick={() => setActiveLayer('IDENTITY_TAX')}
          className={`py-2.5 px-3 border-b-2 font-semibold transition whitespace-nowrap ${
            activeLayer === 'IDENTITY_TAX'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          Identity &amp; Tax ({identityTaxCount})
        </button>
        <button
          onClick={() => setActiveLayer('BANKING')}
          className={`py-2.5 px-3 border-b-2 font-semibold transition whitespace-nowrap ${
            activeLayer === 'BANKING'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          Bank &amp; Account ({bankingCount})
        </button>
        <button
          onClick={() => setActiveLayer('DOCUMENTS')}
          className={`py-2.5 px-3 border-b-2 font-semibold transition whitespace-nowrap ${
            activeLayer === 'DOCUMENTS'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          Documents &amp; Matching ({docMatchingCount})
        </button>
        {attentionCount > 0 && (
          <button
            onClick={() => setActiveLayer('ATTENTION')}
            className={`py-2.5 px-3 border-b-2 font-semibold transition whitespace-nowrap ${
              activeLayer === 'ATTENTION'
                ? 'border-rose-600 text-rose-700'
                : 'border-transparent text-rose-600 hover:text-rose-800'
            }`}
          >
            Needs Attention ({attentionCount})
          </button>
        )}
      </div>

      {/* Findings List */}
      <div className="divide-y divide-slate-100 p-2 sm:p-4">
        {filteredFindings.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500">
            No verification findings recorded in this category.
          </div>
        ) : (
          filteredFindings.map((finding) => (
            <div
              key={finding.id}
              className={`p-4 rounded-lg my-1 transition ${
                finding.status === 'FAILED'
                  ? 'bg-rose-50/40 border border-rose-100'
                  : finding.status === 'WARNING'
                  ? 'bg-amber-50/40 border border-amber-100'
                  : finding.status === 'UNAVAILABLE'
                  ? 'bg-sky-50/40 border border-sky-100'
                  : 'bg-white hover:bg-slate-50/80 border border-transparent'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2.5">
                  {getStatusBadge(finding.status)}
                  <h4 className="text-sm font-semibold text-slate-900">{finding.check_name}</h4>
                  {finding.is_stale && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700">
                      STALE (Doc Replaced)
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-2 text-xs">
                  {getSeverityBadge(finding.status, finding.severity)}
                  <span
                    className="text-slate-400 font-mono text-[10px] cursor-help hidden sm:inline"
                    title={`Internal Verification Check ID: ${finding.check_id}`}
                  >
                    [{finding.check_id}]
                  </span>
                </div>
              </div>

              {/* Plain Language Explanation */}
              <p className="text-xs text-slate-700 mt-2 font-medium leading-relaxed">
                {finding.status === 'UNAVAILABLE'
                  ? finding.explanation.toLowerCase().includes('temporarily') || finding.explanation.toLowerCase().includes('manual')
                    ? finding.explanation
                    : 'The external registry service was temporarily unavailable. A compliance officer will verify this check manually. No action is required from you.'
                  : finding.explanation}
              </p>

              {/* Value Comparison Grid */}
              {(finding.submitted_value || finding.extracted_value || finding.external_value) && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2.5 p-2.5 bg-slate-50 rounded-md border border-slate-200/60 text-xs">
                  {finding.submitted_value && (
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Your Form Entry</span>
                      <span className="font-mono font-medium text-slate-800 break-all">{finding.submitted_value}</span>
                    </div>
                  )}
                  {finding.extracted_value && (
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Found in Uploaded Document</span>
                      <span className="font-mono font-medium text-slate-800 break-all">{finding.extracted_value}</span>
                    </div>
                  )}
                  {finding.external_value && (
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Official Registry Record</span>
                      <span className="font-mono font-medium text-slate-800 break-all">{finding.external_value}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Evidence & Recommended Action */}
              <div className="mt-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                {finding.evidence && (
                  <div className="text-slate-500 text-[11px] italic">
                    Evidence: {finding.evidence}
                  </div>
                )}
                {finding.recommended_action && finding.status !== 'PASSED' && finding.status !== 'UNAVAILABLE' && (
                  <div className="text-indigo-700 font-medium bg-indigo-50 px-2.5 py-1 rounded border border-indigo-100 flex items-center">
                    <span className="font-bold mr-1">Action:</span> {finding.recommended_action}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
