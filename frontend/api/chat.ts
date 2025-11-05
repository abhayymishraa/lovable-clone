import { apiClient } from "./client";
import { ChatResponse, Project } from "./types";

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
   * Get list of user's projects
   */
  listProjects: async (): Promise<{ projects: Project[] }> => {
    const response = await apiClient.get<{ projects: Project[] }>("projects");
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
