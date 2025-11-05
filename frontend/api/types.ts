// API Response Types

export interface UserData {
  id: number;
  email: string;
  name: string;
  tokens_remaining: number;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterResponse {
  access_token: string;
  token_type: string;
  user: UserData;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface ChatResponse {
  status: string;
  message: string;
  chat_id: string;
  tokens_remaining: number;
  reset_in_hours: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}
