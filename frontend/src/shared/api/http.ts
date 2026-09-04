import { API_URL } from "@/shared/config";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(typeof detail?.detail === "string" ? detail.detail : "Не удалось выполнить запрос");
  }
  return response.json() as Promise<T>;
}

export function fileUrl(path: string): string {
  return `${API_URL}${path}`;
}
