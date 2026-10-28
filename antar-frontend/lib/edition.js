/**
 * edition.js — Antar Edition hook and context.
 * Detects whether the backend is running as 'lab' or 'cloud', and exposes
 * the active 'today' date from /api/health.
 */
import { useState, useEffect } from "react";
import { fetchAPI } from "@/lib/api";

let _cachedHealth = null;
let _pendingPromise = null;

export async function fetchServerHealth() {
  if (_cachedHealth) return _cachedHealth;
  if (_pendingPromise) return _pendingPromise;

  _pendingPromise = fetchAPI("/api/health")
    .then((data) => {
      _cachedHealth = data;
      _pendingPromise = null;
      return data;
    })
    .catch((err) => {
      _pendingPromise = null;
      return { edition: "lab", today: "2024-03-10" };
    });

  return _pendingPromise;
}

export function useEdition() {
  const [editionInfo, setEditionInfo] = useState({
    edition: _cachedHealth?.edition || "lab",
    today: _cachedHealth?.today || "2024-03-31",
    isLab: (_cachedHealth?.edition || "lab") === "lab",
    loading: !_cachedHealth,
  });

  useEffect(() => {
    let mounted = true;
    fetchServerHealth().then((data) => {
      if (mounted) {
        setEditionInfo({
          edition: data.edition || "cloud",
          today: data.today || new Date().toISOString().slice(0, 10),
          isLab: (data.edition || "").toLowerCase() === "lab",
          loading: false,
        });
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  return editionInfo;
}
