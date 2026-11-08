import React from 'react';
import { LogOut } from 'lucide-react';
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
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-16 py-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 sm:gap-5 min-w-0">
          <span className="font-serif text-2xl leading-none font-bold tracking-tight text-indigo-700">zamp.</span>
          <span className="h-7 border-l border-slate-200" aria-hidden="true" />
          <div className="min-w-0">
            <div className="font-semibold text-slate-900 text-sm leading-tight truncate">Vendor onboarding</div>
            <div className="text-xs text-slate-500 leading-tight truncate">{user.organisation.name}</div>
          </div>
        </div>

        {/* Right: Role & Profile Controls */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          <NotificationBell />

          <div className="inline-flex items-center gap-1 px-2 sm:px-2.5 py-1 text-xs font-medium text-slate-600 border-l border-slate-200">
            <span className="hidden sm:inline">{roleMeta.label}</span>
            <span className="sm:hidden">{roleMeta.label.split(' ')[0]}</span>
          </div>

          <div className="hidden md:block text-right text-xs text-slate-600">
            <div className="font-medium text-slate-900 leading-tight">{user.full_name}</div>
            <div className="text-[11px] text-slate-500 leading-tight">{user.email}</div>
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
