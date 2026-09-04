import { request } from "@/shared/api/http";
import type { AlertItem } from "@/entities/alert/model";

export const listAlerts = (signal: AbortSignal) => request<AlertItem[]>("/alerts", { signal });
