
(function () {
  const LOG = (...a) => console.log("[BYOB:scrape]", ...a);
  const ERR = (...a) => console.error("[BYOB:scrape]", ...a);

  // Robust money parser
  function parseMoney(s) {
    if (!s) return null;
    const cleaned = s
      .replace(/\s/g, "")
      .replace(/[,\.](?=\d{3}\b)/g, "") // strip thousands separators
      .replace(/[^\d\.,-]/g, "");
    const m = cleaned.match(/-?\d+(?:[.,]\d{1,2})?/);
    if (!m) return null;
    return parseFloat(m[0].replace(",", "."));
  }

  function pickBestNumber(texts) {
    const nums = texts.map(parseMoney).filter(v => typeof v === "number" && !isNaN(v));
    if (!nums.length) return null;
    return Math.min(...nums);
  }

  // Helper: grab multiple candidates by selectors
  function grabText(selectors) {
    const out = [];
    for (const sel of selectors) {
      try {
        document.querySelectorAll(sel).forEach(n => {
          const t = (n.textContent || "").trim();
          if (t) out.push(t);
        });
      } catch (_) {}
    }
    return out;
  }

  // Per-site strategies (update selectors as you learn pages)
  const strategies = {
    // Skyscanner (grid or list result cells)
    skyscanner: () => {
      const texts = grabText([
        "[data-test-id='highest-price']",
        "[data-test-id='price']",
        "[data-test='itinerary-price']",
        "div.Price_mainPrice__",
        ".BpkText_bpk-text__money",
        "[class*='price']"
      ]);
      return pickBestNumber(texts);
    },

    // Kayak result cards
    kayak: () => {
      const texts = grabText([
        "div.resultInner div.price-text",
        "span.price option, span.price",
        "div.flights-price, span.flights-price",
        ".Common-Booking-MultiBookProvider .price-text"
      ]);
      return pickBestNumber(texts);
    },

    // British Airways
    britishairways: () => {
      const texts = grabText([
        ".price-amount",
        "[data-test='price']",
        ".flight-results .total-price",
        ".fare-family .fare-price"
      ]);
      return pickBestNumber(texts);
    },

    // Ryanair
    ryanair: () => {
      const texts = grabText([
        "[data-e2e='fare-card__price']",
        ".journey-card .price",
        ".fare-card .amount",
        "ry-price span",
        "[data-ref='flight-card'] [class*='price']"
      ]);
      return pickBestNumber(texts);
    },

    // easyJet
    easyjet: () => {
      const texts = grabText([
        ".fare-price",
        ".app-components-FaresStyles-FarePrice",
        "[data-test='price']",
        ".basket-total__price",
        "[class*='price'], [class*='fare']"
      ]);
      return pickBestNumber(texts);
    },

    // Expedia
    expedia: () => {
      const texts = grabText([
        "[data-test-id='listing-price-dollars']",
        ".uitk-price-lockup-price",
        ".totalPrice",
        "[data-stid='price-lockup-text']"
      ]);
      return pickBestNumber(texts);
    }
  };

  function hostnameKey(h) {
    if (h.includes("skyscanner")) return "skyscanner";
    if (h.includes("kayak")) return "kayak";
    if (h.includes("britishairways")) return "britishairways";
    if (h.includes("ryanair")) return "ryanair";
    if (h.includes("easyjet")) return "easyjet";
    if (h.includes("expedia")) return "expedia";
    return null;
  }

  function extractRouteFromUrl(url) {
    // Best-effort parse common patterns; backend can refine
    const u = new URL(url);
    const q = Object.fromEntries(u.searchParams.entries());
    // Try common param names
    const origin = q.origin || q.from || q.departure || q["originAirport"] || "";
    const destination = q.destination || q.to || q.arrival || q["destinationAirport"] || "";
    const date = q.date || q.departureDate || q.outDate || q["departDate"] || "";
    return { origin, destination, date };
  }

  // Observe for dynamic loads up to timeout
  function waitForResults(fn, timeoutMs = 15000, pollMs = 800) {
    return new Promise(resolve => {
      const start = Date.now();
      const tryOnce = () => {
        let price = fn();
        if (price && price > 0) return resolve(price);
        if (Date.now() - start >= timeoutMs) return resolve(null);
        setTimeout(tryOnce, pollMs);
      };
      tryOnce();
    });
  }

  async function run() {
    const host = location.hostname;
    const key = hostnameKey(host);
    if (!key) {
      LOG("Host not supported:", host);
      return;
    }

    LOG("Scraper starting for", key, "url:", location.href);

    // Try scrape, wait for SPA to render
    const price = await waitForResults(strategies[key], 20000, 900);

    if (!price) {
      LOG("No price found after waiting. Giving up.");
      return;
    }

    // Try to infer currency symbol near the price (very rough)
    let currency = (document.body.innerText.match(/[€£$]|EUR|GBP|USD/) || [""])[0];

    const route = extractRouteFromUrl(location.href);

    const payload = {
      vendor: key,
      url: location.href,
      price,
      currency: currency || "",
      route,
      pageTitle: document.title || "",
    };

    LOG("Price extracted:", payload);

    chrome.runtime.sendMessage({
      type: "BYOB_SCRAPE_RESULT",
      data: payload,
      userAgent: navigator.userAgent
    }, (res) => {
      LOG("BG ack:", res);
    });
  }

  // Debounce re-runs on SPA changes
  let lastHref = location.href;
  const observer = new MutationObserver(() => {
    if (location.href !== lastHref) {
      lastHref = location.href;
      LOG("URL changed (SPA). Re-running scraper.");
      run().catch(ERR);
    }
  });
  observer.observe(document, { subtree: true, childList: true });

  // Initial run
  run().catch(ERR);
})();
