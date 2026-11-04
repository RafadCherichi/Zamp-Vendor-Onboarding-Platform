export interface DatabaseHealth {
  status: string;
  dialect: string;
  latency_ms: number;
  error?: string | null;
}

export interface StorageHealth {
  backend: string;
  status: string;
  path_or_bucket: string;
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
  database: DatabaseHealth;
  storage: StorageHealth;
}
