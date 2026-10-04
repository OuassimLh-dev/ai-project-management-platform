import axios from "axios";
import { z } from "zod";
import { clearToken, getToken } from "../auth/tokenStorage";
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/+$/, "");
export const transport = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}
const errorSchema = z.object({ detail: z.unknown() });
function safeDetail(status: number, body: unknown, token: string | null) {
  if (status >= 500) return "The service is unavailable. Please try again.";
  if (status === 422) return "Please check the form values and try again.";
  const parsed = errorSchema.safeParse(body);
  if (parsed.success && typeof parsed.data.detail === "string") {
    const detail = token
      ? parsed.data.detail.split(token).join("[redacted]")
      : parsed.data.detail;
    return detail.slice(0, 300);
  }
  const messages: Record<number, string> = {
    400: "This change is not allowed.",
    401: "Please sign in again.",
    403: "You do not have permission to do that.",
    404: "This resource is unavailable.",
  };
  return messages[status] || "The request could not be completed.";
}
export const errorMessage = (error: unknown) =>
  error instanceof ApiError
    ? error.detail
    : "Something went wrong. Please try again.";
type Options = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  params?: object;
  authenticated?: boolean;
  timeout?: number;
};
export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  options: Options = {},
): Promise<T> {
  const token = options.authenticated === false ? null : getToken();
  try {
    const response = await transport.request<unknown>({
      url: path,
      method: options.method ?? "GET",
      data: options.body,
      params: options.params,
      timeout: options.timeout ?? transport.defaults.timeout,
      headers: {
        ...(options.body !== undefined
          ? { "Content-Type": "application/json" }
          : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    const parsed = schema.safeParse(
      response.status === 204 ? undefined : response.data,
    );
    if (!parsed.success)
      throw new ApiError(502, "The service returned an unexpected response.");
    return parsed.data;
  } catch (error: unknown) {
    if (error instanceof ApiError) throw error;
    if (axios.isAxiosError<unknown>(error)) {
      const status = error.response?.status ?? 0;
      if (status === 401 && token && getToken() === token) clearToken();
      throw new ApiError(
        status,
        status
          ? safeDetail(status, error.response?.data, token)
          : "Unable to reach the service. Check your connection and try again.",
      );
    }
    throw new ApiError(0, "The request could not be completed.");
  }
}
