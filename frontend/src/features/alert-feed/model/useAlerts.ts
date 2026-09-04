"use client";

import { useResource } from "@/shared/lib/useResource";
import type { AlertItem } from "@/entities/alert/model";
import { listAlerts } from "../api/alertsApi";

export const useAlerts = () => useResource<AlertItem[]>(listAlerts);
