import { ref, watch, onMounted, onUnmounted } from "vue";

export type ThemeType = "system" | "light" | "dark";

export function useTheme() {
  const theme = ref<ThemeType>("system");
  const isDark = ref(true);

  let mediaQuery: MediaQueryList | null = null;

  const applyTheme = (t: ThemeType) => {
    let activeTheme: "light" | "dark" = "dark";

    if (t === "system") {
      activeTheme = mediaQuery?.matches ? "dark" : "light";
    } else {
      activeTheme = t;
    }

    isDark.value = activeTheme === "dark";

    if (activeTheme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  };

  const handleSystemThemeChange = (e: MediaQueryListEvent) => {
    if (theme.value === "system") {
      applyTheme("system");
    }
  };

  onMounted(() => {
    // 监听系统主题变化
    mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.addEventListener("change", handleSystemThemeChange);

    // 从 localStorage 读取设定
    const savedTheme = localStorage.getItem("renderai-theme") as ThemeType;
    if (savedTheme && ["system", "light", "dark"].includes(savedTheme)) {
      theme.value = savedTheme;
    }

    applyTheme(theme.value);
  });

  onUnmounted(() => {
    mediaQuery?.removeEventListener("change", handleSystemThemeChange);
  });

  const setTheme = (newTheme: ThemeType) => {
    theme.value = newTheme;
    localStorage.setItem("renderai-theme", newTheme);
    applyTheme(newTheme);
  };

  return {
    theme,
    isDark,
    setTheme,
  };
}
