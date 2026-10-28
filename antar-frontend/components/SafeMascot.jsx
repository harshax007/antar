"use client";

// page-mascot's <Mascot>, with its sprite sheets loaded first.
//
// The library paints each sheet as a CSS background-image: a request that fails leaves the
// agent blank, with no error and no retry. On the Catalyst host a different few of the
// thirty sheets went missing on every load (2026-10-27), and the host serves them as
// application/octet-stream. Here each sheet is fetched once per page, four at a time,
// retried with a short back-off, and handed to the library as a blob URL typed
// image/webp. The agent is drawn when both of its sheets have arrived; if one never
// does, the plain URL is used, which is no worse than before.

import { useEffect, useState } from "react";
import { Mascot as PageMascot } from "page-mascot";

const ready = new Map();     // url -> Promise<string> (blob URL, or the url itself)
const queue = [];
let active = 0;
const PARALLEL = 4;
const TRIES = 3;

function pump() {
  while (active < PARALLEL && queue.length) {
    const job = queue.shift();
    active += 1;
    job().finally(() => { active -= 1; pump(); });
  }
}

async function fetchSheet(url) {
  for (let i = 0; i < TRIES; i += 1) {
    try {
      const res = await fetch(url, { cache: i ? "reload" : "default" });
      if (res.ok) {
        const buf = await res.arrayBuffer();
        if (buf.byteLength > 0) return URL.createObjectURL(new Blob([buf], { type: "image/webp" }));
      }
    } catch {}
    await new Promise((r) => setTimeout(r, 400 * (i + 1)));
  }
  return url;
}

function load(url) {
  if (!ready.has(url)) {
    ready.set(url, new Promise((resolve) => {
      queue.push(() => fetchSheet(url).then(resolve));
      pump();
    }));
  }
  return ready.get(url);
}

export function Mascot({ directions, reactions, size = 40, className, ...rest }) {
  const [urls, setUrls] = useState(null);
  useEffect(() => {
    let live = true;
    setUrls(null);
    Promise.all([load(directions), load(reactions)]).then(([d, r]) => { if (live) setUrls([d, r]); });
    return () => { live = false; };
  }, [directions, reactions]);
  if (!urls) return <span className={className} aria-hidden="true" style={{ display: "block", flexShrink: 0, width: size, height: size }} />;
  return <PageMascot {...rest} className={className} size={size} directions={urls[0]} reactions={urls[1]} />;
}

export default Mascot;
