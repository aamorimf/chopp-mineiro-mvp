function apiUrl(path) {
  const normalizedBaseUrl = window.API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  return `${normalizedBaseUrl}${normalizedPath}`;
}

async function apiFetch(path, options = {}) {
  let response;

  try {
    response = await fetch(apiUrl(path), options);
  } catch (error) {
    throw new Error("Network error");
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const data = await response.json();

      if (data && data.detail) {
        message = data.detail;
      }
    } catch (error) {
      // Keep generic status message when response is not JSON.
    }

    throw new Error(message);
  }

  return response;
}

window.apiUrl = apiUrl;
window.apiFetch = apiFetch;
