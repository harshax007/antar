// Public-asset URL helper.
//
// Catalyst serves the exported site under /app/ (see next.config.mjs), so the production
// build sets basePath: "/app". Next rewrites <Link href> and next/image for you, but it
// does NOT rewrite:
//   • raw fetch("/karnataka.json")
//   • plain <img src="/brand/logo.png"> / <video src="/brand/video/x.mp4">
//
// Those resolve against the domain ROOT and 404 in production. Wrapping them in asset()
// keeps one source working in both places: no prefix under `next dev`, "/app" prefix in
// the export.
//
// Before this existed the codebase hardcoded "/app/…" into a few paths to make production
// work, which is precisely why they 404'd on localhost.

export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

/**
 * Resolve a path in `public/` to a URL valid for the current deployment.
 *   asset("/brand/logo.png")  ->  "/brand/logo.png"      (dev)
 *                             ->  "/app/brand/logo.png"  (Catalyst export)
 */
export function asset(path) {
  if (!path) return BASE_PATH || "/";
  // Already absolute (http(s):, data:, blob:) - leave it alone.
  if (/^[a-z][a-z0-9+.-]*:/i.test(path) || path.startsWith("//")) return path;
  const clean = path.startsWith("/") ? path : `/${path}`;
  // Guard against double-prefixing if a caller passes an already-resolved path.
  if (BASE_PATH && clean.startsWith(`${BASE_PATH}/`)) return clean;
  return `${BASE_PATH}${clean}`;
}
