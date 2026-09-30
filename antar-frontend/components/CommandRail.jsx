"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLang } from "./Providers";

const NAV = [
  { href: "/ask", icon: "", label_en: "Chat", label_kn: "ಚಾಟ್" },
  { href: "/network", icon: "", label_en: "Brain", label_kn: "ಬ್ರೈನ್" },
  { href: "/map", icon: "", label_en: "Map", label_kn: "ನಕ್ಷೆ" },
  { href: "/predict", icon: "", label_en: "Predict", label_kn: "ಮುನ್ಸೂಚನೆ" },
  { href: "/profiles", icon: "", label_en: "Search", label_kn: "ಹುಡುಕಾಟ" },
  { href: "/admin", icon: "", label_en: "Account", label_kn: "ಖಾತೆ" },
];

export default function CommandRail() {
  const pathname = usePathname();
  const { lang } = useLang();

  return (
    <nav className="command-rail glass">
      {NAV.map((n) => {
        const isActive = pathname === n.href;
        return (
          <Link key={n.href} href={n.href} className={`rail-item ${isActive ? "active" : ""}`}>
            <span className="icon">{n.icon}</span>
            <span className="label">{lang === "kn" ? n.label_kn : n.label_en}</span>
          </Link>
        );
      })}
    </nav>
  );
}
