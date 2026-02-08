export interface AuthRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  user_id: string;
  email: string;
}

export interface User {
  user_id: string;
  email: string;
}
