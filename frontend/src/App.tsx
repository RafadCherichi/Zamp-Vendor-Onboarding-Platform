import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { LoginView } from './components/views/LoginView';
import { ProcurementDashboard } from './components/views/ProcurementDashboard';
import { VendorDashboard } from './components/views/VendorDashboard';
import { ReviewerDashboard } from './components/views/ReviewerDashboard';
import { AdminDashboard } from './components/views/AdminDashboard';
import { InviteLandingView } from './components/views/InviteLandingView';
import { HealthCard } from './components/HealthCard';
import { fetchHealth } from './api/client';
import type { HealthResponse } from './types/api';
import { Activity, ChevronDown, ChevronUp } from 'lucide-react';

const MainAppContent: React.FC = () => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [showDiagnostics, setShowDiagnostics] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    // Check if the current browser path is an invitation link: /invite/<token>
    const path = window.location.pathname;
    if (path.startsWith('/invite/')) {
      const token = path.replace('/invite/', '').trim();
      if (token) {
        setInviteToken(token);
      }
    }
  }, []);

  const loadHealthData = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: any) {
      setHealthError(err?.message || 'Failed to ping health endpoint');
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    if (showDiagnostics && !health) {
      loadHealthData();
    }
  }, [showDiagnostics, health]);

  if (inviteToken) {
    return (
      <InviteLandingView
        token={inviteToken}
        onGoToLogin={() => {
          window.history.pushState({}, '', '/');
          setInviteToken(null);
        }}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center text-xs text-slate-500 gap-3">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        Initializing session and verifying organisation context...
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <LoginView />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Role-Specific Scoped Landing */}
        {user.role === 'procurement_officer' && <ProcurementDashboard />}
        {user.role === 'vendor' && <VendorDashboard />}
        {user.role === 'reviewer' && <ReviewerDashboard />}
        {user.role === 'admin' && <AdminDashboard />}

        {/* Collapsible System Health & Diagnostics */}
        <div className="pt-4 border-t border-slate-200">
          <button
            onClick={() => setShowDiagnostics((prev) => !prev)}
            className="flex items-center justify-between w-full p-3 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
          >
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-600" />
              <span>Foundation Environment Diagnostics (Database & Object Storage Health)</span>
            </div>
            {showDiagnostics ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showDiagnostics && (
            <div className="mt-3">
              <HealthCard
                health={health}
                loading={healthLoading}
                error={healthError}
                onRefresh={loadHealthData}
              />
            </div>
          )}
        </div>
      </main>

      <footer className="bg-white border-t border-slate-200 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div>
            Vendor Onboarding Platform &bull; India Edition &bull; Increment 1 Identity & App Shell
          </div>
          <div>
            Organisation Scoped: <span className="font-semibold text-slate-700">{user.organisation.name}</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainAppContent />
    </AuthProvider>
  );
};

export default App;
