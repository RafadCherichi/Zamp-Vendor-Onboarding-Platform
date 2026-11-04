import React from 'react';
import { Building2, LogOut, ShieldCheck, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import type { Role } from '../types/auth';
import { NotificationBell } from './notifications/NotificationBell';

const ROLE_BADGES: Record<Role, { label: string; bg: string; text: string; border: string }> = {
  admin: {
    label: 'Administrator',
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
  },
  procurement_officer: {
    label: 'Procurement Officer',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
  },
  reviewer: {
    label: 'Reviewer / Approver',
    bg: 'bg-amber-50',
    text: 'text-amber-800',
    border: 'border-amber-200',
  },
  vendor: {
    label: 'Vendor Contact',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
  },
};

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  if (!user) return null;

  const roleMeta = ROLE_BADGES[user.role] || {
    label: user.role,
    bg: 'bg-slate-50',
    text: 'text-slate-700',
    border: 'border-slate-200',
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand & Organisation Identity */}
        <div className="flex items-center space-x-4">
          <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-xs">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 tracking-tight text-base">
                Vendor Onboarding Platform
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                v1.0
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Building2 className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-medium text-slate-700">{user.organisation.name}</span>
              <span className="text-slate-300">&bull;</span>
              <span className="text-slate-400">Org ID: {user.organisation.slug}</span>
            </div>
          </div>
        </div>

        {/* Right: Role & Profile Controls */}
        <div className="flex items-center space-x-3">
          <NotificationBell />

          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${roleMeta.bg} ${roleMeta.text} ${roleMeta.border}`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            {roleMeta.label}
          </div>

          <div className="hidden md:flex items-center gap-2 pl-2 border-l border-slate-200 text-xs text-slate-600">
            <div className="w-7 h-7 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-semibold">
              <User className="w-4 h-4 text-slate-500" />
            </div>
            <div className="text-left">
              <div className="font-medium text-slate-900 leading-tight">{user.full_name}</div>
              <div className="text-[11px] text-slate-500 leading-tight">{user.email}</div>
            </div>
          </div>

          <button
            onClick={logout}
            title="Sign out of your session"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </div>
    </header>
  );
};
