import { asset } from "@/lib/assets";

export const BRAND = {
  name: "Antar",
  tagline_en: "Think. Connect. Anticipate.",
  tagline_kn: "ಆಲೋಚಿಸಿ. ಸಂಪರ್ಕಿಸಿ. ನಿರೀಕ್ಷಿಸಿ.",
  // was "/brand/logo.png" - that file does not exist in public/ and 404s wherever
  // logo_main is rendered. The real primary mark is antar_final_logo.png.
  logo_main: asset("/brand/antar_final_logo.png"),
  logo_sub: asset("/brand/sub-logo/sub-logo.png"),
  usage: {
    header: "mark_wordmark",
    login: "mark_wordmark",
    rail: "mark_only"
  }
};
