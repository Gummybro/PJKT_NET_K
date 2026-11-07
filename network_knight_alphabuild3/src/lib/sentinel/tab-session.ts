import { api } from "./store";

const key = "network-knight.tab";
const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
export const tabId = (navigation?.type === "reload" && sessionStorage.getItem(key)) || crypto.randomUUID();
sessionStorage.setItem(key, tabId);
let ready: Promise<unknown> | undefined;
export function openSession() {
  return ready ??= api('/api/log-sessions/' + tabId, {method:'POST',headers:{'X-Network-Knight':'dashboard'}})
    .catch(error => { ready = undefined; throw error; });
}
