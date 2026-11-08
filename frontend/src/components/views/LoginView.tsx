import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Lock, Mail, ShieldAlert, ArrowRight } from 'lucide-react';

interface DemoAccount {
  email: string;
  name: string;
  role: string;
  org: string;
  tagColor: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    email: 'admin@apex.com',
    name: 'Aditya Sharma',
    role: 'Administrator',
    org: 'Apex Enterprises Ltd.',
    tagColor: 'bg-purple-50 text-purple-700 border-purple-200',
  },
  {
    email: 'procurement@apex.com',
    name: 'Pooja Verma',
    role: 'Procurement Officer',
    org: 'Apex Enterprises Ltd.',
    tagColor: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  {
    email: 'reviewer@apex.com',
    name: 'Rajesh Iyer',
    role: 'Reviewer / Approver',
    org: 'Apex Enterprises Ltd.',
    tagColor: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  {
    email: 'vendor.mismatch@sharmaworks.in',
    name: 'Ramesh Sharma',
    role: 'Vendor (Action Required)',
    org: 'Sharma Engineering Works',
    tagColor: 'bg-amber-100 text-amber-800 border-amber-300 font-bold',
  },
  {
    email: 'vendor@apexcomponents.com',
    name: 'Vikram Malhotra',
    role: 'Vendor (Clean Case)',
    org: 'Apex Components Ltd.',
    tagColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  {
    email: 'procurement@zenith.com',
    name: 'Zoya Akhtar',
    role: 'Procurement (Tenant B)',
    org: 'Zenith Global Corp',
    tagColor: 'bg-slate-100 text-slate-700 border-slate-300',
  },
];

export const LoginView: React.FC = () => {
  const { login, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch {
      // Handled by AuthContext error state
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (demoEmail: string) => {
    clearError();
    setEmail(demoEmail);
    setPassword('Password123!');
    setIsSubmitting(true);
    try {
      await login(demoEmail, 'Password123!');
    } catch {
      // Error handled
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 lg:grid lg:grid-cols-2">
      <div className="bg-indigo-700 text-white px-6 py-12 sm:px-12 lg:px-16 lg:py-20 flex flex-col justify-between">
        <div className="font-serif text-3xl font-bold tracking-tight">zamp.</div>
        <div className="max-w-lg py-10 lg:py-20">
          <p className="text-xs uppercase tracking-[0.2em] text-indigo-200 mb-5">Vendor operations</p>
          <h1 className="font-serif text-4xl sm:text-5xl leading-tight tracking-tight">
            A clearer path from invitation to decision.
          </h1>
          <p className="mt-6 text-base leading-relaxed text-indigo-100 max-w-md">
            Share your business details once. See what needs attention, what is under review, and why a decision was made.
          </p>
        </div>
        <p className="text-xs text-indigo-200">A working case study prototype for Indian vendor onboarding.</p>
      </div>

      <div className="w-full px-4 py-10 sm:px-10 lg:px-16 lg:py-16 flex flex-col justify-center">
        <div className="w-full max-w-md mx-auto">
          <p className="text-xs uppercase tracking-[0.16em] font-semibold text-indigo-700">Workspace access</p>
          <h2 className="text-3xl font-semibold text-slate-900 mt-2">
            Sign in
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Continue with your invitation or choose a demo role below.
          </p>
        </div>

      <div className="mt-8 w-full max-w-md mx-auto">
        <div className="bg-white py-8 px-6 border border-slate-200 rounded-lg sm:px-8">
          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 flex items-start gap-2.5 text-xs text-rose-700">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Business Email
              </label>
              <div className="relative rounded-lg shadow-2xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative rounded-lg shadow-2xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-xs text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? 'Authenticating...' : 'Sign In to Workspace'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Login Switcher */}
          <div className="mt-6 pt-6 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Quick-Login Demo Accounts
              </span>
              <span className="text-[10px] font-mono text-slate-400">PW: Password123!</span>
            </div>
            <p className="text-xs text-slate-500 mb-3 leading-tight">
              Select any role to instantly authenticate and evaluate its scoped workspace:
            </p>

            <div className="space-y-2">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => handleQuickLogin(acc.email)}
                  className="w-full text-left p-2.5 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center gap-2.5">
                    <div>
                      <div className="text-xs font-semibold text-slate-900 leading-tight">
                        {acc.name}
                      </div>
                      <div className="text-[11px] text-slate-500 leading-tight">
                        {acc.email} &bull; <span className="text-slate-400">{acc.org}</span>
                      </div>
                    </div>
                  </div>
                  <span
                    className="text-[11px] font-medium px-2 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-600"
                  >
                    {acc.role}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};
