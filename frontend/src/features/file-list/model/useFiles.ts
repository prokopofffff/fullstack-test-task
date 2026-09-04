"use client";

import { useResource } from "@/shared/lib/useResource";
import { hasPending, type FileItem } from "@/entities/file/model";
import { listFiles } from "../api/filesApi";

export const useFiles = () => useResource<FileItem[]>(listFiles, { pollWhile: hasPending });
