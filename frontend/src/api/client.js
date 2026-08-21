const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8010").replace(/\/+$/, "");

async function fetchWithRetry(url, options) {
  const method = (options.method || "GET").toUpperCase();
  const attempts = method === "GET" || method === "HEAD" ? 3 : 1;
  let lastError;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await fetch(url, options);
    } catch (error) {
      lastError = error;
      if (attempt < attempts - 1) await new Promise(resolve => setTimeout(resolve, 350 * (attempt + 1)));
    }
  }
  throw new Error("Cannot reach the CityCare backend. Please confirm the backend is running on port 8010 and refresh the page.", {cause:lastError});
}

export async function api(path, options = {}) {
  const token = localStorage.getItem("citycare_token");
  const requestOptions = { ...options, headers: { "Content-Type":"application/json", ...(token ? {Authorization:`Bearer ${token}`} : {}), ...options.headers } };
  const response = await fetchWithRetry(`${API}${path}`, requestOptions);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) { if (response.status === 401) localStorage.removeItem("citycare_token"); const detail=Array.isArray(data.detail)?data.detail.map(item=>item.msg).join(". "):data.detail; throw new Error(detail || "Something went wrong. Please try again."); }
  return data;
}

export async function apiFile(path) {
  const token = localStorage.getItem("citycare_token");
  const response = await fetchWithRetry(`${API}${path}`, {headers: token ? {Authorization:`Bearer ${token}`} : {}});
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Unable to download this file.");
  }
  return response.blob();
}
