
const $ = sel => document.querySelector(sel);

chrome.storage.sync.get({ baseUrl: "", apiKey: "" }, ({ baseUrl, apiKey }) => {
  $("#baseUrl").value = baseUrl;
  $("#apiKey").value = apiKey;
});

$("#save").addEventListener("click", () => {
  const baseUrl = $("#baseUrl").value.trim().replace(/\/+$/, "");
  const apiKey  = $("#apiKey").value.trim();
  chrome.storage.sync.set({ baseUrl, apiKey }, () => {
    $("#status").textContent = "Saved.";
    setTimeout(() => $("#status").textContent = "", 1500);
  });
});
