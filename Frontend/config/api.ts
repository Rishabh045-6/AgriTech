import { Platform } from 'react-native';

const FALLBACK_IP_ADDRESS = '10.67.6.75';
const PORT = 3001;

const envIp = typeof process !== 'undefined' ? process.env?.IP_ADDRESS : undefined;
const IP_ADDRESS = envIp?.trim() || FALLBACK_IP_ADDRESS;

const DEV_HOSTS = Platform.OS === 'android'
  ? [IP_ADDRESS, '10.0.2.2', '127.0.0.1', 'localhost']
  : [IP_ADDRESS, '127.0.0.1', 'localhost'];

const uniqueHosts = Array.from(new Set(DEV_HOSTS.filter(Boolean)));

export const API_BASE_URL = __DEV__
  ? `http://${uniqueHosts[0]}:${PORT}`
  : 'https://your-agritech-backend.azurewebsites.net';

export const API_BASE_URL_CANDIDATES = __DEV__
  ? uniqueHosts.map(host => `http://${host}:${PORT}`)
  : [API_BASE_URL];

const withTimeout = async (url: string, init?: RequestInit, timeoutMs = 8000) => {
  // abort controller lets us cancel slow requests (model endpoints can take longer)
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
};

const isConnectionError = (error: unknown) => {
  if (!(error instanceof Error)) {
    return false;
  }

  return error.name === 'AbortError' || error.message.toLowerCase().includes('network request failed');
};

export const apiFetch = async (
  path: string,
  init?: RequestInit,
  timeoutMs: number = 8000 // allow callers to override when necessary (model runs etc.)
) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const triedUrls: string[] = [];

  for (const baseUrl of API_BASE_URL_CANDIDATES) {
    const fullUrl = `${baseUrl}${normalizedPath}`;
    triedUrls.push(fullUrl);

    try {
      return await withTimeout(fullUrl, init, timeoutMs);
    } catch (error) {
      if (!isConnectionError(error)) {
        throw error;
      }
    }
  }

  throw new Error(
    `Unable to reach backend. Tried: ${triedUrls.join(', ')}. Check IP_ADDRESS in frontend .env and make sure backend is running on port ${PORT}.`
  );
};

export { IP_ADDRESS };
