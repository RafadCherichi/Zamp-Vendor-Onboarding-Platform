import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { LoginView } from './components/views/LoginView';
import { ProcurementDashboard } from './components/views/ProcurementDashboard';
import { VendorDashboard } from './components/views/VendorDashboard';
import { ReviewerDashboard } from './components/views/ReviewerDashboard';
import { AdminDashboard } from './components/views/AdminDashboard';
import { InviteLandingView } from './components/views/InviteLandingView';

const MainAppContent: React.FC = () => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [inviteToken, setInviteToken] = useState<string | null>(null);

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
        Opening your workspace...
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

      </main>

      <footer className="bg-white border-t border-slate-200 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div>
            Vendor onboarding
          </div>
          <div>
            Organisation: <span className="font-semibold text-slate-700">{user.organisation.name}</span>
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
