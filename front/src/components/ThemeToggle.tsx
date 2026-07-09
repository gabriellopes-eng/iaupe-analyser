"use client";

import { SunIcon } from "@/components/icons";

// Alterna o tema claro/escuro carimbando data-theme no elemento raiz,
// que sobrepoe a media query prefers-color-scheme nos dois sentidos.
export default function ThemeToggle() {
  function toggle() {
    const root = document.documentElement;
    const current = root.getAttribute("data-theme");
    const isDark = current
      ? current === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.setAttribute("data-theme", isDark ? "light" : "dark");
  }

  return (
    <button className="theme-btn" type="button" onClick={toggle} aria-label="Alternar tema claro e escuro">
      <SunIcon />
      <span>Tema</span>
    </button>
  );
}
