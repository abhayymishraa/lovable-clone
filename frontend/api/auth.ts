import { apiClient } from "./client";
import {
  LoginResponse,
  RegisterResponse,
  LoginRequest,
  RegisterRequest,
  UserData,
} from "./types";

/**
 * Auth API Service
 */
export const authApi = {
  /**
   * Login user
   */
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>(
      "/auth/login",
      credentials,
    );
    return response.data;
  },

  /**
   * Register new user
   */
  register: async (data: RegisterRequest): Promise<RegisterResponse> => {
    const response = await apiClient.post<RegisterResponse>(
      "/auth/register",
      data,
    );
    return response.data;
  },

  /**
   * Get current user data (refresh user info)
   */
  getCurrentUser: async (): Promise<UserData> => {
    const response = await apiClient.get<UserData>("/auth/me");
    return response.data;
  },
};
