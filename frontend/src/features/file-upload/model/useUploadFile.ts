"use client";

import { useState, type FormEvent } from "react";
import { uploadFile } from "../api/uploadFile";

export function useUploadFile(onSuccess?: () => void) {
  const [title, setTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!title.trim() || !selectedFile) {
      setError("Укажите название и выберите файл");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const formData = new FormData();
    formData.append("title", title.trim());
    formData.append("file", selectedFile);

    try {
      await uploadFile(formData);
      setTitle("");
      setSelectedFile(null);
      onSuccess?.();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Произошла ошибка");
    } finally {
      setIsSubmitting(false);
    }
  }

  return { title, setTitle, selectedFile, setSelectedFile, isSubmitting, error, submit };
}
