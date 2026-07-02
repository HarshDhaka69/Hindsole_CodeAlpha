/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // Warm off-white / charcoal neutral scale (not corporate grey/blue)
        neutral: {
          50: "#FAF7F2",
          100: "#F2ECE2",
          150: "#E9E0D2",
          200: "#DDD2C0",
          300: "#C2B3A0",
          400: "#A0907D",
          500: "#7D6F60",
          600: "#5C5048",
          700: "#43392F",
          800: "#2B2622",
          850: "#211D1A",
          900: "#171411",
          950: "#0E0C0A",
        },
        // Burnt orange accent — the one bold color, used sparingly
        accent: {
          50: "#FDF0E7",
          100: "#FADCC4",
          200: "#F3B583",
          300: "#EA8C4C",
          400: "#DE6A2C",
          500: "#C3501A",
          600: "#9E3F15",
          700: "#7B3112",
          800: "#5C2410",
          900: "#3F190B",
        },
        success: {
          500: "#3E7D52",
          600: "#2F6240",
        },
        error: {
          500: "#B6442C",
          600: "#963522",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["'Fraunces'", "Georgia", "serif"],
      },
      fontSize: {
        "fluid-xs": "clamp(0.72rem, 0.68rem + 0.2vw, 0.8rem)",
        "fluid-sm": "clamp(0.82rem, 0.78rem + 0.2vw, 0.92rem)",
        "fluid-base": "clamp(0.95rem, 0.9rem + 0.25vw, 1.05rem)",
        "fluid-lg": "clamp(1.05rem, 1rem + 0.4vw, 1.25rem)",
        "fluid-xl": "clamp(1.25rem, 1.1rem + 0.7vw, 1.6rem)",
        "fluid-2xl": "clamp(1.55rem, 1.3rem + 1.2vw, 2.1rem)",
        "fluid-3xl": "clamp(2rem, 1.6rem + 2vw, 3.1rem)",
        "fluid-4xl": "clamp(2.6rem, 2rem + 3vw, 4.4rem)",
        "fluid-5xl": "clamp(3.2rem, 2.4rem + 4.5vw, 6rem)",
      },
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
        "safe-top": "env(safe-area-inset-top)",
        "safe-bottom": "env(safe-area-inset-bottom)",
        "safe-left": "env(safe-area-inset-left)",
        "safe-right": "env(safe-area-inset-right)",
      },
      borderRadius: {
        soft: "0.875rem",
        card: "1.25rem",
      },
      boxShadow: {
        soft: "0 2px 18px -4px rgb(0 0 0 / 0.08)",
        lifted: "0 12px 32px -8px rgb(0 0 0 / 0.16)",
        "inner-soft": "inset 0 1px 2px rgb(0 0 0 / 0.04)",
      },
      transitionDuration: {
        350: "350ms",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out forwards",
        "skeleton-pulse": "skeletonPulse 1.4s ease-in-out infinite",
        "slide-up": "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "slide-in-right": "slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: 0, transform: "translateY(8px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        skeletonPulse: {
          "0%, 100%": { opacity: 0.55 },
          "50%": { opacity: 1 },
        },
        slideUp: {
          "0%": { transform: "translateY(100%)" },
          "100%": { transform: "translateY(0)" },
        },
        slideInRight: {
          "0%": { transform: "translateX(100%)" },
          "100%": { transform: "translateX(0)" },
        },
      },
    },
    screens: {
      xs: "375px",
      sm: "481px",
      md: "768px",
      lg: "1024px",
      xl: "1440px",
    },
  },
  plugins: [],
};
