import React, { useState, useEffect } from 'react';
import { apiValidateInvitationToken } from '../../api/invitations';
import type { InvitationPublicResponse } from '../../types/invitation';
import { Building2, CheckCircle2, XCircle, Clock, ArrowRight } from 'lucide-react';

interface InviteLandingViewProps {
  token: string;
  onGoToLogin: () => void;
}

export const InviteLandingView: React.FC<InviteLandingViewProps> = ({ token, onGoToLogin }) => {
  const [data, setData] = useState<InvitationPublicResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function validate() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiValidateInvitationToken(token);
        setData(res);
      } catch (err: any) {
        setError(err?.message || 'Failed to validate invitation token.');
      } finally {
        setLoading(false);
      }
    }
    validate();
  }, [token]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md mb-4">
          <Building2 className="w-7 h-7" />
        </div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Vendor Onboarding Portal
        </h1>
        <p className="mt-1 text-xs text-slate-500">
          Official Buyer Onboarding Verification &bell; India Edition
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-2xl sm:px-8 space-y-5">
          {loading ? (
            <div className="py-8 text-center text-slate-400 text-xs flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              Validating invitation token and buyer context...
            </div>
          ) : error ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-3">
                <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-bold text-rose-900">Invalid Invitation Link</h3>
                  <p className="mt-1">{error}</p>
                  <p className="mt-2 text-rose-600">
                    Please ensure the full URL was copied or contact your procurement representative
                    for a replacement link.
                  </p>
                </div>
              </div>
              <button
                onClick={onGoToLogin}
                className="w-full py-2 px-4 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition-colors"
              >
                Return to Login
              </button>
            </div>
          ) : data ? (
            <div className="space-y-4">
              {data.is_valid ? (
                <>
                  <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 space-y-2">
                    <div className="font-bold flex items-center gap-1.5 text-emerald-900">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      Valid Invitation Confirmed
                    </div>
                    <p>
                      You have been invited by{' '}
                      <span className="font-semibold text-emerald-950">
                        {data.buyer_organisation_name}
                      </span>{' '}
                      to complete your vendor verification profile.
                    </p>
                  </div>

                  <div className="space-y-2.5 pt-2 text-xs text-slate-600">
                    <div>
                      <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider">
                        Invited Vendor Entity
                      </span>
                      <div className="font-semibold text-slate-900 text-sm">{data.vendor_name}</div>
                    </div>
                    <div>
                      <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider">
                        Contact Business Email
                      </span>
                      <div className="font-mono text-slate-700">{data.vendor_email}</div>
                    </div>
                    <div>
                      <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider">
                        Link Expiry Date
                      </span>
                      <div className="text-slate-700">
                        {new Date(data.expires_at).toLocaleString()}
                      </div>
                    </div>
                    {data.message && (
                      <div>
                        <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider">
                          Buyer Message
                        </span>
                        <div className="italic text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-200 mt-1">
                          &ldquo;{data.message}&rdquo;
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Dev Simulation Notice */}
                  <div className="p-3 rounded-lg bg-indigo-50 border border-indigo-200 text-[11px] text-indigo-900">
                    <span className="font-bold">[DEVELOPMENT DEMO MECHANISM]</span>
                    <p className="mt-0.5">
                      This token was generated by the procurement officer. In Increment 2, clicking
                      below opens the 6-section vendor application form.
                    </p>
                  </div>

                  <button
                    onClick={onGoToLogin}
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors"
                  >
                    <span>Proceed to Sign In / Onboarding</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </>
              ) : (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 space-y-2">
                    <div className="font-bold flex items-center gap-1.5 text-amber-900">
                      <Clock className="w-4 h-4 text-amber-600" />
                      Invitation Inactive ({data.status})
                    </div>
                    <p>{data.message}</p>
                  </div>
                  <button
                    onClick={onGoToLogin}
                    className="w-full py-2 px-4 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition-colors"
                  >
                    Return to Login
                  </button>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
