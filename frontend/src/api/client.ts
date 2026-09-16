/**
 * Axios HTTP client with JWT authentication.
 *
 * - Automatically attaches the JWT Bearer token to every request.
 * - Normalizes API errors into a consistent format.
 * - Sets the base URL from environment variables.
 */

import axios, { type AxiosError, type AxiosInstance } from "axios";
import type { ApiError } from "@/types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30_000,
});

// Auto-initialize token from localStorage if present
const savedToken = localStorage.getItem("token");
if (savedToken) {
  apiClient.defaults.headers.common["Authorization"] = `Bearer ${savedToken}`;
}

/**
 * Attach a JWT Bearer token to all outgoing requests.
 */
export function setAuthToken(token: string | null): void {
  if (token) {
    apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete apiClient.defaults.headers.common["Authorization"];
  }
}

/**
 * Type guard: check if an error is an API error response.
 */
export function isApiError(error: unknown): error is AxiosError<ApiError> {
  return axios.isAxiosError(error);
}

/**
 * Extract a human-readable message from an API error.
 */
export function getApiErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return (
      error.response?.data?.error?.message ??
      (error.response?.data as { detail?: string })?.detail ??
      error.message ??
      "An unexpected error occurred"
    );
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred";
}

export function getApiErrorCode(error: unknown): string | undefined {
  if (isApiError(error)) {
    return error.response?.data?.error?.code;
  }
  return undefined;
}
