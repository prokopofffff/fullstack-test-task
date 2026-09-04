import { request } from "@/shared/api/http";
import type { FileItem } from "@/entities/file/model";

export const uploadFile = (formData: FormData) =>
  request<FileItem>("/files", { method: "POST", body: formData });
