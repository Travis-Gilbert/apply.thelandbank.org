/**
 * GCLBA Application Portal — Tailwind CSS Configuration
 *
 * Ported from the inline CDN config in base.html. Color tokens, fonts, and
 * utilities match the existing class names used throughout 20+ templates.
 *
 * Civic green  = completion signals, program header, ack cards
 * Civic blue   = navigation, interaction, focus rings
 * Warm neutrals = ambient backgrounds, field dividers
 * Program      = per-program identity accent (cards, borders)
 */

module.exports = {
  content: [
    // Theme app templates
    "../templates/**/*.html",
    // Main templates directory (BASE_DIR/templates)
    "../../templates/**/*.html",
    // Templates in all Django apps
    "../../**/templates/**/*.html",
    // Cotton components
    "../../templates/cotton/**/*.html",
    // Crispy template pack
    "../../crispy_gclba/templates/**/*.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ["Bitter", "Georgia", "serif"],
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        civic: {
          green: {
            50: "#f0f7f1",
            100: "#dceede",
            200: "#b8ddb9",
            600: "#2e7d32",
            700: "#256929",
            800: "#1b5e20",
            900: "#0d3311",
          },
          blue: {
            50: "#eff4f8",
            100: "#dae6f0",
            200: "#b4cde0",
            500: "#3d7ea6",
            600: "#2d6a8a",
            700: "#1e5673",
            800: "#184862",
          },
        },
        program: {
          featured: {
            DEFAULT: "#2E7D32",
            light: "#E8F5E9",
            border: "#b8ddb9",
          },
          rehab: {
            DEFAULT: "#F57C00",
            light: "#FFF3E0",
            border: "#FFE0B2",
          },
          vip: {
            DEFAULT: "#1565C0",
            light: "#E3F2FD",
            border: "#BBDEFB",
          },
        },
        warm: {
          50: "#FAF6F1",
          100: "#F2EDE6",
          200: "#EAE4DC",
          300: "#DDD6CC",
          400: "#CCC7BF",
          500: "#A09890",
          600: "#7A746C",
          700: "#5A5550",
          800: "#3A3632",
          900: "#2A2622",
        },

        // Semantic status colors (for staff dashboard badges)
        status: {
          submitted: "#2563eb",
          "under-review": "#d97706",
          "docs-requested": "#9333ea",
          approved: "#16a34a",
          denied: "#dc2626",
          withdrawn: "#6b7280",
        },

        // Surface tokens (for future component library use)
        surface: {
          DEFAULT: "#ffffff",
          alt: "#f9fafb",
          muted: "#f3f4f6",
        },
        muted: "#6b7280",
      },

      borderRadius: {
        card: "8px",
        pill: "9999px",
      },

      boxShadow: {
        card: "0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)",
        "card-hover":
          "0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)",
        focus: "0 0 0 3px rgba(22, 163, 74, 0.2)",
      },

      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
      },

      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
    require("@tailwindcss/aspect-ratio"),
  ],
};
