export type Role = 'vendor' | 'procurement_officer' | 'reviewer' | 'admin';

export interface OrganisationInfo {
  id: string;
  name: string;
  slug: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  organisation: OrganisationInfo;
}

export interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
