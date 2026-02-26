import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import {
  getHealth,
  getAccessToken,
  setAccessToken,
  clearAccessToken,
  verifyAccessToken,
} from "./api";
import { createDiscreteApi, darkTheme } from "naive-ui";

// Styles
import "./assets/css/variables.css";
import "./assets/css/base.css";
import "./assets/css/components.css";
import "./assets/css/home.css";
import "./assets/css/history.css";

const { message } = createDiscreteApi(["message"], {
  configProviderProps: {
    theme: darkTheme,
    themeOverrides: {
      common: {
        primaryColor: "#00ff88",
        primaryColorHover: "#33ff99",
        primaryColorPressed: "#00cc6a",
        primaryColorSuppl: "#00ff88",
      },
    },
  },
});

async function ensureApiAccess(): Promise<boolean> {
  const health = await getHealth();
  if (!health.success || !health.auth_required) {
    return true;
  }

  let token = getAccessToken();

  for (let i = 0; i < 3; i++) {
    if (!token) {
      token = (window.prompt("请输入访问令牌:") || "").trim();
    }

    if (!token) {
      message.warning("需要访问令牌才能使用本系统。");
      continue;
    }

    setAccessToken(token);
    const ok = await verifyAccessToken();
    if (ok) {
      return true;
    }

    clearAccessToken();
    token = "";
    message.error("访问令牌无效，请重试。");
  }

  document.body.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#333;">
      认证失败，无法进入系统。
    </div>
  `;
  return false;
}

async function bootstrap() {
  const canEnter = await ensureApiAccess();
  if (!canEnter) return;

  const app = createApp(App as any);
  app.use(createPinia());
  app.use(router as any);
  app.mount("#app");
}

bootstrap();
