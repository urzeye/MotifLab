import { createApp } from "vue";
import { h, ref } from "vue";
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
import { createDiscreteApi, darkTheme, NInput } from "naive-ui";

// Styles
import "./assets/css/variables.css";
import "./assets/css/base.css";
import "./assets/css/components.css";
import "./assets/css/home.css";
import "./assets/css/history.css";

const { message, dialog } = createDiscreteApi(["message", "dialog"], {
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

function requestAccessToken(): Promise<string | null> {
  return new Promise((resolve) => {
    const tokenValue = ref("");
    let settled = false;

    const finish = (value: string | null) => {
      if (settled) return;
      settled = true;
      resolve(value);
      modal.destroy();
    };

    const modal = dialog.create({
      title: "访问令牌认证",
      content: () =>
        h("div", { style: "display:flex;flex-direction:column;gap:12px;" }, [
          h(
            "div",
            { style: "font-size:14px;color:var(--text-sub,#a1a1aa);" },
            "请输入访问令牌以继续使用系统"
          ),
          h(NInput, {
            type: "password",
            value: tokenValue.value,
            placeholder: "输入 MOTIFLAB_AUTH_TOKEN",
            showPasswordOn: "mousedown",
            autofocus: true,
            onUpdateValue: (value: string) => {
              tokenValue.value = value;
            },
            onKeydown: (event: KeyboardEvent) => {
              if (event.key !== "Enter") return;
              event.preventDefault();
              const nextToken = tokenValue.value.trim();
              if (!nextToken) {
                message.warning("请输入访问令牌。");
                return;
              }
              finish(nextToken);
            },
          }),
        ]),
      positiveText: "确认",
      negativeText: "取消",
      closable: false,
      closeOnEsc: false,
      maskClosable: false,
      onPositiveClick: () => {
        const nextToken = tokenValue.value.trim();
        if (!nextToken) {
          message.warning("请输入访问令牌。");
          return false;
        }
        finish(nextToken);
        return true;
      },
      onNegativeClick: () => {
        finish(null);
        return true;
      },
      onClose: () => {
        finish(null);
      },
    });
  });
}

async function ensureApiAccess(): Promise<boolean> {
  const health = await getHealth();
  if (!health.success || !health.auth_required) {
    return true;
  }

  let token = getAccessToken();

  for (let i = 0; i < 3; i++) {
    if (!token) {
      token = ((await requestAccessToken()) || "").trim();
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
