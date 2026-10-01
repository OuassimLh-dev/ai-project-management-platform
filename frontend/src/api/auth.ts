import { request } from "./client";
import {
  tokenSchema,
  userSchema,
  type LoginInput,
  type RegisterInput,
} from "../types/api";
export const authApi = {
  login: (body: LoginInput) =>
    request("/auth/login", tokenSchema, {
      method: "POST",
      body,
      authenticated: false,
    }),
  register: (body: RegisterInput) =>
    request("/auth/register", userSchema, {
      method: "POST",
      body,
      authenticated: false,
    }),
  me: () => request("/auth/me", userSchema),
};
