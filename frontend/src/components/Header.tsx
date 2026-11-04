import React from 'react';
import { Building2 } from 'lucide-react';

interface HeaderProps {
  isBackendHealthy: boolean | null;
}

export const Header: React.FC<HeaderProps> = ({ isBackendHealthy }) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-lg text-slate-900 leading-tight">
                Vendor Onboarding Platform
              </h1>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                India Edition
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              Invitation-first • AI-assisted • Human-controlled
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-medium bg-slate-50 border-slate-200">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isBackendHealthy === true
                  ? 'bg-emerald-500 ring-2 ring-emerald-200'
                  : isBackendHealthy === false
                  ? 'bg-rose-500 ring-2 ring-rose-200'
                  : 'bg-amber-400 animate-pulse'
              }`}
            />
            <span className="text-slate-700">
              {isBackendHealthy === true
                ? 'Backend Online'
                : isBackendHealthy === false
                ? 'Backend Offline'
                : 'Connecting...'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
