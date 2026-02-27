export const safeParseJson = <T>(raw: string | null, fallback: T): T => {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

export const getStorageItem = (key: string): string | null => {
  try {
    if (typeof window === "undefined" || !window.localStorage) return null;
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
};

export const setStorageItem = (key: string, value: string) => {
  try {
    if (typeof window === "undefined" || !window.localStorage) return;
    window.localStorage.setItem(key, value);
  } catch {
    // ignore
  }
};

export const removeStorageItem = (key: string) => {
  try {
    if (typeof window === "undefined" || !window.localStorage) return;
    window.localStorage.removeItem(key);
  } catch {
    // ignore
  }
};

export const getStringFromStorage = (key: string, fallback = ""): string =>
  (getStorageItem(key) || fallback).toString();

export const getArrayFromStorage = (key: string): string[] => {
  const raw = getStorageItem(key);
  const parsed = safeParseJson<unknown>(raw, []);
  if (!Array.isArray(parsed)) return [];
  return parsed.filter(
    (item): item is string => typeof item === "string" && item.trim().length > 0
  );
};

export const setJsonToStorage = (key: string, value: unknown) =>
  setStorageItem(key, JSON.stringify(value));

export const getSessionItem = (key: string): string | null => {
  try {
    if (typeof window === "undefined" || !window.sessionStorage) return null;
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
};

export const setSessionItem = (key: string, value: string) => {
  try {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    window.sessionStorage.setItem(key, value);
  } catch {
    // ignore
  }
};

export const removeSessionItem = (key: string) => {
  try {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    window.sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
};

export const getJsonFromSession = <T>(key: string, fallback: T): T =>
  safeParseJson<T>(getSessionItem(key), fallback);

export const setJsonToSession = (key: string, value: unknown) =>
  setSessionItem(key, JSON.stringify(value));
