export type ProcessingStatus = "uploaded" | "processing" | "processed" | "failed";

export type FileItem = {
  id: string;
  title: string;
  original_name: string;
  mime_type: string;
  size: number;
  processing_status: ProcessingStatus;
  scan_status: string | null;
  scan_details: string | null;
  metadata_json: Record<string, unknown> | null;
  requires_attention: boolean;
  created_at: string;
  updated_at: string;
};

const TERMINAL: ReadonlySet<ProcessingStatus> = new Set(["processed", "failed"]);

export const isTerminal = (file: FileItem): boolean => TERMINAL.has(file.processing_status);
export const hasPending = (files: FileItem[]): boolean => files.some((file) => !isTerminal(file));

export function processingVariant(status: ProcessingStatus): string {
  if (status === "failed") return "danger";
  if (status === "processing") return "warning";
  if (status === "processed") return "success";
  return "secondary";
}
