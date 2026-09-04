"use client";

import { useCallback } from "react";
import { useResource } from "@/shared/lib/useResource";
import type { AlertItem } from "@/entities/alert/model";
import { listAlerts } from "../api/alertsApi";

export function useAlerts(shouldPoll: boolean) {
  const pollWhile = useCallback(() => shouldPoll, [shouldPoll]);
  return useResource<AlertItem[]>(listAlerts, { pollWhile });
}
