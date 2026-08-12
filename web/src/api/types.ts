export interface ApiErrorDetail {
  code: string;
  message: string;
  field: string | null;
}

export interface ApiErrorEnvelope {
  error: ApiErrorDetail;
  request_id: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface UserAccount {
  user_id: string;
  email: string;
  is_active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AccessToken {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface CurrentUser extends UserAccount {
  profile_ids: string[];
}
