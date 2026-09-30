// ponytail: Vanilla IndexedDB wrapper to cache the Second Brain safely.
// Minimal overhead, async, handles heavy JSON payloads effortlessly.

const DB_NAME = "AntarBrainDB";
const STORE_NAME = "BrainStore";

export function getBrainCache() {
  return new Promise((resolve) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = (e) => e.target.result.createObjectStore(STORE_NAME);
    req.onsuccess = (e) => {
      const db = e.target.result;
      const tx = db.transaction(STORE_NAME, "readonly");
      const getReq = tx.objectStore(STORE_NAME).get("brain_graph");
      getReq.onsuccess = () => resolve(getReq.result);
      getReq.onerror = () => resolve(null);
    };
    req.onerror = () => resolve(null);
  });
}

export function setBrainCache(data) {
  return new Promise((resolve) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = (e) => e.target.result.createObjectStore(STORE_NAME);
    req.onsuccess = (e) => {
      const db = e.target.result;
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).put(data, "brain_graph");
      tx.oncomplete = () => resolve();
    };
  });
}

export function clearBrainCache() {
  return new Promise((resolve) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onsuccess = (e) => {
      if (!e.target.result.objectStoreNames.contains(STORE_NAME)) return resolve();
      const db = e.target.result;
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).clear();
      tx.oncomplete = () => resolve();
    };
  });
}
