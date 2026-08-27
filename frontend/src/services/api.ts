export interface HealthResponse {
  status: string;
  service: string;
}

const BACKEND_URL = "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    if (!response.ok) {
      return null;
    }
    return await response.json();
  } catch {
    // Graceful fallback if backend is unreachable
    return null;
  }
}
