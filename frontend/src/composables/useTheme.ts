import { ref } from "vue";

export type ThemeType = "system" | "light" | "dark";

const STORAGE_KEY = "motiflab-theme";
const theme = ref<ThemeType>("system");
const isDark = ref(true);

let mediaQuery: MediaQueryList | null = null;
let initialized = false;
let listenerRegistered = false;

const isValidTheme = (value: string | null): value is ThemeType =>
  value === "system" || value === "light" || value === "dark";

const resolveActiveTheme = (targetTheme: ThemeType): "light" | "dark" => {
  if (targetTheme === "system") {
    return mediaQuery?.matches ? "dark" : "light";
  }
  return targetTheme;
};

const applyTheme = (targetTheme: ThemeType) => {
  const activeTheme = resolveActiveTheme(targetTheme);
  isDark.value = activeTheme === "dark";

  if (activeTheme === "light") {
    document.documentElement.setAttribute("data-theme", "light");
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  document.documentElement.style.colorScheme = activeTheme;
};

const ensureMediaQuery = () => {
  if (typeof window === "undefined") {
    return;
  }

  if (!mediaQuery) {
    mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  }

  if (!listenerRegistered && mediaQuery) {
    mediaQuery.addEventListener("change", () => {
      if (theme.value === "system") {
        applyTheme("system");
      }
    });
    listenerRegistered = true;
  }
};

const initializeTheme = () => {
  if (initialized || typeof window === "undefined") {
    return;
  }

  ensureMediaQuery();

  const savedTheme = localStorage.getItem(STORAGE_KEY);
  if (isValidTheme(savedTheme)) {
    theme.value = savedTheme;
  }

  applyTheme(theme.value);
  initialized = true;
};

export function useTheme() {
  initializeTheme();

  const setTheme = (newTheme: ThemeType) => {
    ensureMediaQuery();
    theme.value = newTheme;
    localStorage.setItem(STORAGE_KEY, newTheme);
    applyTheme(newTheme);
  };

  return {
    theme,
    isDark,
    setTheme,
  };
}
