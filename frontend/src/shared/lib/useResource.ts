"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Options<T> = { pollWhile?: (data: T) => boolean; intervalMs?: number };

export function useResource<T>(fetcher: (signal: AbortSignal) => Promise<T>, options: Options<T> = {}) {
  const { pollWhile, intervalMs = 2000 } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const loadedRef = useRef(false);

  const load = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    if (loadedRef.current) setIsRefreshing(true);
    try {
      const next = await fetcher(controller.signal);
      if (controller.signal.aborted) return;
      setData(next);
      setError(null);
      loadedRef.current = true;
    } catch (cause) {
      if (controller.signal.aborted) return;
      setError(cause instanceof Error ? cause.message : "Произошла ошибка");
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [fetcher]);

  useEffect(() => {
    void load();
    return () => controllerRef.current?.abort();
  }, [load]);

  useEffect(() => {
    if (!data || !pollWhile || !pollWhile(data)) return;
    const timer = setTimeout(() => void load(), intervalMs);
    return () => clearTimeout(timer);
  }, [data, pollWhile, intervalMs, load]);

  return { data, isLoading, isRefreshing, error, refresh: load };
}
