import "./globals.css";

export const metadata = {
  title: "Antar - Crime Intelligence",
  description: "Multi-agent crime intelligence for Karnataka State Police",
};

import { ThemeProvider, LangProvider } from "@/components/Providers";

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Preload critical local fonts for instant zero-latency paint */}
        <link rel="preload" href="/fonts/jersey-10-latin.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/inter-400.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/inter-600.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/chakra-petch-600.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DotGothic16&family=Silkscreen:wght@400;700&family=Chakra+Petch:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Kannada:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;700;800&family=Instrument+Serif:ital@1&family=Josefin+Sans:wght@400;500;600;700&family=Roboto:wght@400;500;700&family=Jersey+10&family=Anek+Kannada:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
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
