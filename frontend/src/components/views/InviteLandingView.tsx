import React, { useState, useEffect } from 'react';
import { apiValidateInvitationToken } from '../../api/invitations';
import { apiAcceptInvitation } from '../../api/applications';
import type { InvitationPublicResponse } from '../../types/invitation';
import { Building2, CheckCircle2, XCircle, Clock, Lock, User, ShieldCheck } from 'lucide-react';

interface InviteLandingViewProps {
  token: string;
  onGoToLogin: () => void;
}

export const InviteLandingView: React.FC<InviteLandingViewProps> = ({ token, onGoToLogin }) => {
  const [data, setData] = useState<InvitationPublicResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Acceptance form state
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isAccepting, setIsAccepting] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

  useEffect(() => {
    async function validate() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiValidateInvitationToken(token);
        setData(res);
        if (res.vendor_name) {
          setFullName(res.vendor_name);
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to validate invitation token.');
      } finally {
        setLoading(false);
      }
    }
    validate();
  }, [token]);

  const handleAccept = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setAcceptError('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setAcceptError('Passwords do not match.');
      return;
    }

    setIsAccepting(true);
    setAcceptError(null);
    try {
      const res = await apiAcceptInvitation(token, password, fullName);
      // Store token and reload into the vendor onboarding wizard
      localStorage.setItem('vop_auth_token', res.access_token);
      window.location.href = '/';
    } catch (err: any) {
      setAcceptError(err?.message || 'Failed to establish vendor account.');
      setIsAccepting(false);
    }
  };

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
          Official Buyer Onboarding Verification &bull; India Edition
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
                      Invitation Confirmed
                    </div>
                    <p>
                      You have been invited by{' '}
                      <span className="font-bold text-emerald-950">
                        {data.buyer_organisation_name}
                      </span>{' '}
                      to submit your vendor profile.
                    </p>
                  </div>

                  <div className="space-y-2 pt-1 text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Vendor Entity:</span>
                      <span className="font-semibold text-slate-900">{data.vendor_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Contact Email:</span>
                      <span className="font-mono text-slate-700">{data.vendor_email}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Expires:</span>
                      <span className="text-slate-700">{new Date(data.expires_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {data.message && (
                    <div className="text-xs italic text-slate-600 bg-indigo-50/50 p-2.5 rounded-lg border border-indigo-100">
                      &ldquo;{data.message}&rdquo;
                    </div>
                  )}

                  {/* Account Creation Form */}
                  <form onSubmit={handleAccept} className="space-y-3 pt-2">
                    <div className="border-t border-slate-100 pt-3">
                      <h4 className="text-xs font-bold text-slate-900 mb-1">
                        Set Password to Establish Vendor Account
                      </h4>
                      <p className="text-[11px] text-slate-500 mb-3">
                        You will use this password to save progress, resume your onboarding, and track verification.
                      </p>
                    </div>

                    {acceptError && (
                      <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
                        {acceptError}
                      </div>
                    )}

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                        Representative Full Name
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                          <User className="w-3.5 h-3.5" />
                        </div>
                        <input
                          type="text"
                          required
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          placeholder="Your full name"
                          className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                        Choose Password
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                          <Lock className="w-3.5 h-3.5" />
                        </div>
                        <input
                          type="password"
                          required
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="Minimum 8 characters"
                          className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                        Confirm Password
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                          <Lock className="w-3.5 h-3.5" />
                        </div>
                        <input
                          type="password"
                          required
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="Re-type password"
                          className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isAccepting}
                      className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50 mt-2"
                    >
                      <ShieldCheck className="w-4 h-4" />
                      <span>{isAccepting ? 'Establishing Account...' : 'Accept Invitation & Start Onboarding'}</span>
                    </button>
                  </form>
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
