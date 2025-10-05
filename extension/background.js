// FlightAlert Pro BYOB - Background Service Worker
// Strong console tagging
const tag = (...args) => console.log("[BYOB:bg]", ...args);
const err = (...args) => console.error("[BYOB:bg]", ...args);

// Retry POST with exponential backoff
async function postWithRetry(url, payload, headers, maxRetries = 3) {
  for (let i=0; i<=maxRetries; i++) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json().catch(() => ({}));
    } catch (e) {
      if (i === maxRetries) throw e;
      const backoff = 400 * Math.pow(2, i);
      tag(`POST failed (attempt ${i+1}/${maxRetries+1}): ${e}. Retrying in ${backoff}ms`);
      await new Promise(r => setTimeout(r, backoff));
    }
  }
}

// Receive scraped data from content script
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "BYOB_SCRAPE_RESULT") {
    chrome.storage.sync.get({ baseUrl: "", apiKey: "" }, async ({ baseUrl, apiKey }) => {
      try {
        if (!baseUrl) {
          err("No baseUrl configured in Options. Open extension options and set it.");
          return;
        }
        const url = `${baseUrl}/api/ingest`;
        const headers = {};
        if (apiKey) headers["X-API-Key"] = apiKey;

        // Include tab info and userAgent to help backend classify
        const payload = {
          ...msg.data,
          userAgent: msg.userAgent || "",
          tabUrl: sender?.tab?.url || "",
          ts: new Date().toISOString()
        };

        tag("Posting scrape to backend:", url, payload);
        const resJson = await postWithRetry(url, payload, headers);
        tag("Backend ack:", resJson);
      } catch (e) {
        err("Failed to POST to backend:", e);
      }
    });
  }
  sendResponse && sendResponse({ ok: true });
  return true;
});

// For SPAs: re-inject on history changes too
chrome.webNavigation.onHistoryStateUpdated.addListener(details => {
  tag("SPA navigation detected on tab", details.tabId, details.url);
});

chrome.runtime.onInstalled.addListener(() => tag("Installed/Updated."));