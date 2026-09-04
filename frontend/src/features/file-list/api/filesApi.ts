import { fileUrl, request } from "@/shared/api/http";
import type { FileItem } from "@/entities/file/model";

export const listFiles = (signal: AbortSignal) => request<FileItem[]>("/files", { signal });
export const downloadUrl = (id: string) => fileUrl(`/files/${id}/download`);
