/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0f1115",
          raised: "#171a21",
          border: "#262b36",
        },
        accent: {
          DEFAULT: "#7c5cff",
          hover: "#8f74ff",
        },
      },
    },
  },
  plugins: [],
};
