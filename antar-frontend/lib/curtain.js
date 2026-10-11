// One curtain across the sign-in hand-off.
//
// Signing in used to show three things in a row - a "verifying" beat, a loading overlay
// that belonged to the login page, and then the chat screen fading in from nothing. The
// overlay went away with the page it lived in, so for a moment between the two there was
// neither: a flash of bare background, then the next animation starting cold.
//
// The curtain is a plain element on <body>, outside React, so it is still there while one
// page is replaced by the next. Sign-in raises it; the screen that arrives lowers it once
// it has drawn. If nothing lowers it (a failed navigation), it lowers itself.

const ID = "antar-curtain";

export function raiseCurtain() {
  if (typeof document === "undefined" || document.getElementById(ID)) return;
  const el = document.createElement("div");
  el.id = ID;
  el.setAttribute("aria-hidden", "true");
  el.innerHTML = "<span><i></i></span>";
  document.body.appendChild(el);
  // a beat, so the browser has the element at opacity 0 before it is asked for 1. A timer
  // rather than an animation frame: frames stop in a background tab, and a curtain that
  // waits on one would never rise or fall there.
  setTimeout(() => el.classList.add("up"), 20);
  el._timer = setTimeout(lowerCurtain, 9000);
}

export function lowerCurtain() {
  if (typeof document === "undefined") return;
  const el = document.getElementById(ID);
  if (!el || el.dataset.leaving) return;
  el.dataset.leaving = "1";
  clearTimeout(el._timer);
  el.classList.remove("up");
  setTimeout(() => el.remove(), 420);
}
