/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        pt: "#C8102E",
        sucesso: "#16A34A",
        atencao: "#CA8A04",
        alerta: "#DC2626",
        info: "#2563EB",
        // status do mapa
        consolidado: "#15803D",
        em_construcao: "#65A30D",
        disputado: "#CA8A04",
        adverso: "#DC2626",
        indefinido: "#9CA3AF",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
