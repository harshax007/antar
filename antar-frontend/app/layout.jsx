import "./globals.css";
import "./apple-feel.css";
import "./design-tokens.css";
import "./responsive.css";

export const metadata = {
  title: "Antar - Crime Intelligence",
  description: "Multi-agent crime intelligence for Karnataka State Police",
};

import { ThemeProvider, LangProvider } from "@/components/Providers";
import { asset } from "@/lib/assets";

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Preload critical local fonts for instant zero-latency paint */}
        <link rel="preload" href={asset("/fonts/jersey-10-latin.woff2")} as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href={asset("/fonts/inter-400.woff2")} as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href={asset("/fonts/inter-600.woff2")} as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href={asset("/fonts/chakra-petch-600.woff2")} as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DotGothic16&family=Silkscreen:wght@400;700&family=Chakra+Petch:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Kannada:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;700;800&family=Instrument+Serif:ital@1&family=Josefin+Sans:wght@400;500;600;700&family=Roboto:wght@400;500;700&family=Jersey+10&family=Anek+Kannada:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        {/* Phones open a little zoomed out (0.9): the screens fit ~10% more at once. Only
            phones - a tablet at 0.9 would cross the 820px line into the desktop layout. The
            officer can still pinch to zoom. Run again on DOMContentLoaded in case Next's
            viewport tag comes later in <head> than this script. */}
        <script dangerouslySetInnerHTML={{ __html: `
          (function () {
            function fit() {
              if (Math.min(screen.width, screen.height) > 480) return;
              document.querySelectorAll('meta[name="viewport"]').forEach(function (m) {
                m.setAttribute('content', 'width=device-width, initial-scale=0.9');
              });
            }
            fit();
            document.addEventListener('DOMContentLoaded', fit);
            // Next re-adds its own viewport tag on the client; set the phone scale on that too
            if (Math.min(screen.width, screen.height) <= 480 && window.MutationObserver) {
              new MutationObserver(function (list) {
                for (var i = 0; i < list.length; i++) {
                  var n = list[i].target.nodeName === 'META' ? list[i].target : null;
                  var added = list[i].addedNodes || [];
                  for (var j = 0; j < added.length; j++) if (added[j].nodeName === 'META') n = added[j];
                  if (n && n.getAttribute('name') === 'viewport' && n.getAttribute('content').indexOf('0.9') < 0) { fit(); return; }
                }
              }).observe(document.head, { childList: true, subtree: true, attributes: true, attributeFilter: ['content'] });
            }
          })();
        `}} />
        <script dangerouslySetInnerHTML={{ __html: `
          if (document.cookie.includes('fonts_cached=1')) {
            document.documentElement.classList.add('fonts-loaded');
          } else {
            document.fonts.ready.then(function() {
              document.cookie = 'fonts_cached=1; max-age=31536000; path=/';
              document.documentElement.classList.add('fonts-loaded');
            });
          }
        `}} />
      </head>
      <body>
        <ThemeProvider>
          <LangProvider>
            {children}
          </LangProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
