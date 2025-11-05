import { apiClient } from "./client";
import { ChatResponse } from "./types";

/**
 * Chat API Service
 */
export const chatApi = {
  /**
   * Create or start a new chat
   */
  createChat: async (prompt: string): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>("/chat", { prompt });
    return response.data;
  },

  /**
   * Check if a URL is accessible (health check)
   */
  checkUrlHealth: async (url: string): Promise<boolean> => {
    try {
      const response = await apiClient.head(url, {
        timeout: 5000, // 5 seconds for health check
      });
      return response.status === 200;
    } catch {
      return false;
    }
  },
};
