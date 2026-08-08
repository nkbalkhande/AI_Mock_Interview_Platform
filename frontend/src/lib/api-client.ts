import axios, { type AxiosInstance } from "axios";

import { API_BASE_URL } from "@/lib/constants";

/**
 * Central Axios instance. All feature `api.ts` modules should import this
 * rather than calling axios/fetch directly, so auth handling, base URL and
 * error normalization live in one place (repository-like API layer).
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Normalize the backend error envelope: { error: { code, message } }.
    const normalized = error?.response?.data?.error ?? {
      code: "network_error",
      message: error?.message ?? "Request failed",
    };
    return Promise.reject(normalized);
  },
);
