// API configuration for Cointainr
window.COINTAINR_API_CONFIG = {
  // Base URL for API requests
  apiBaseUrl: window.location.origin + "/api/v1",

  // Helper function to create API URLs
  createApiUrl: function (path) {
    // If path already starts with http:// or https://, return it as is
    if (path.startsWith("http://") || path.startsWith("https://")) {
      return path;
    }

    // If path starts with a slash, remove it
    if (path.startsWith("/")) {
      path = path.substring(1);
    }

    // Return the full URL
    return this.apiBaseUrl + "/" + path;
  },
};

// Override the URL constructor to handle relative URLs
const originalURL = window.URL;
window.URL = function (url, base) {
  // If the URL starts with /api/v1, convert it to an absolute URL
  if (typeof url === "string" && url.startsWith("/api/v1")) {
    url = window.location.origin + url;
  }

  // Call the original URL constructor
  return new originalURL(url, base);
};
window.URL.prototype = originalURL.prototype;
window.URL.createObjectURL = originalURL.createObjectURL;
window.URL.revokeObjectURL = originalURL.revokeObjectURL;

console.log("API configuration loaded");
