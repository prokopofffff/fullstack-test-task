export type AlertLevel = "info" | "warning" | "critical";

export type AlertItem = {
  id: number;
  file_id: string;
  level: AlertLevel;
  message: string;
  created_at: string;
};

export function levelVariant(level: AlertLevel): string {
  if (level === "critical") return "danger";
  if (level === "warning") return "warning";
  return "success";
}
