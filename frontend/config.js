(function () {
  const configParams = new URLSearchParams(window.location.search);
  const apiFromUrl = configParams.get("api_base_url");

  console.log("URL PARAM:", window.location.search);
  console.log("API FROM URL:", apiFromUrl);

  window.API_BASE_URL = apiFromUrl || "http://127.0.0.1:8000";
})();