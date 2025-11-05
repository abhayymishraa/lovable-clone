import axios from "axios";

// API Base URL - change based on environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Create axios instance with default config
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor - Add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const token = localStorage.getItem("auth_token");

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle 401 Unauthorized - redirect to login
    if (error.response?.status === 401) {
      // Clear auth data
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_data");

      // Redirect to signin if not already there
      if (!window.location.pathname.includes("/signin")) {
        window.location.href = "/signin";
      }
    }

    // Return a formatted error
    const errorMessage =
      (error.response?.data as { detail?: string })?.detail || error.message;
    return Promise.reject(new Error(errorMessage));
  },
);

export default apiClient;
