<template>
  <div class="container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ isGenerating ? "正在生成" : "创作完成" }}</h1>
        <p class="page-subtitle">
          <span v-if="isGenerating">
            图片生成中：{{ store.progress.current }} /
            {{ store.progress.total }}，文案并行生成中
          </span>
          <span v-else-if="failedCount > 0">
            已完成 {{ doneCount }} 张，失败 {{ failedCount }} 张，可单张重试
          </span>
          <span v-else>
            恭喜，你的小红书图文已全部生成完成，共 {{ store.images.length }} 张
          </span>
        </p>
      </div>
      <div class="header-actions" style="display: flex; gap: 12px">
        <button class="btn" @click="startOver">再来一篇</button>
        <button class="btn" @click="downloadAll" :disabled="isGenerating">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          一键下载
        </button>
        <button
          class="btn btn-primary"
          @click="goToPublish"
          :disabled="!canPublish"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M22 2L11 13"></path>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
          发布到小红书
        </button>
      </div>
    </div>

    <div
      class="card"
      style="padding: 20px 32px"
      v-if="store.progress.total > 0"
    >
      <div class="progress-row">
        <span class="progress-label">图片进度</span>
        <span class="progress-value">{{ Math.round(progressPercent) }}%</span>
      </div>
      <div class="progress-track">
        <div
          class="progress-bar"
          :style="{ width: `${progressPercent}%` }"
        ></div>
      </div>
      <p v-if="errorText" class="error-text">
        {{ errorText }}
      </p>
    </div>

    <div class="card" style="padding: 32px">
      <div class="grid-cols-4">
        <div
          v-for="image in store.images"
          :key="image.index"
          class="image-card group"
        >
          <div
            v-if="image.url"
            class="result-image-wrap"
            @click="openPreview(image.url)"
          >
            <img
              :src="image.url"
              :alt="`第 ${image.index + 1} 页`"
              class="result-image"
            />
            <div
              v-if="regeneratingIndex === image.index"
              class="result-image-overlay regenerating-overlay"
              @click.stop
            >
              <div class="spinner"></div>
              <span class="overlay-text">重绘中...</span>
            </div>
            <div v-else class="result-image-overlay hover-overlay">
              <div class="glass-zoom-icon">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  <line x1="11" y1="8" x2="11" y2="14"></line>
                  <line x1="8" y1="11" x2="14" y2="11"></line>
                </svg>
              </div>
            </div>
            <button
              v-if="regeneratingIndex !== image.index"
              class="overlay-regenerate-btn floating-regenerate-btn always-visible"
              @click.stop="handleRegenerate(image)"
              :disabled="regeneratingIndex === image.index || isGenerating"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M23 4v6h-6"></path>
                <path d="M1 20v-6h6"></path>
                <path
                  d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
                ></path>
              </svg>
              <span>{{
                regeneratingIndex === image.index ? "重绘中..." : "重绘此页"
              }}</span>
            </button>
            <span
              v-if="regeneratingIndex !== image.index"
              class="preview-tip-always"
              >点击图片预览大图</span
            >
          </div>

          <div v-else class="result-image-wrap placeholder-wrap">
            <div
              v-if="
                image.status === 'generating' || image.status === 'retrying'
              "
              class="placeholder-state"
            >
              <div class="spinner"></div>
              <span>{{
                image.status === "retrying" ? "重试中..." : "生成中..."
              }}</span>
            </div>
            <div
              v-else-if="image.status === 'error'"
              class="placeholder-state error-state"
            >
              <span>生成失败</span>
            </div>
            <div v-else class="placeholder-state">
              <span>等待中</span>
            </div>
          </div>

          <div class="result-image-footer">
            <span class="footer-page-info">
              <i>Page {{ image.index + 1 }}</i>
            </span>
            <button
              class="pill-download-btn"
              @click="downloadOne(image)"
              :disabled="!image.url"
            >
              下载
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="previewVisible" class="preview-modal" @click="closePreview">
      <button class="preview-close" type="button" @click.stop="closePreview">
        x
      </button>
      <img
        class="preview-image"
        :src="previewImageUrl"
        alt="预览大图"
        @click.stop
      />
    </div>

    <ContentDisplay />
  </div>
</template>

<style scoped>
.header-actions .btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: var(--radius-md);
}

.progress-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-label {
  font-size: 13px;
  color: var(--text-sub);
}

.progress-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-info);
}

.progress-track {
  height: 8px;
  border-radius: 999px;
  background: var(--bg-active);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--color-info);
  transition: width 0.25s ease;
}

.error-text {
  margin-top: 10px;
  color: var(--color-error, #ff4d4f);
  font-size: 13px;
}

.image-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
  transition: all var(--transition-base);
}

.image-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: var(--border-hover);
}

.result-image-wrap {
  position: relative;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  cursor: pointer;
  line-height: 0;
  background: var(--bg-elevated);
}

.placeholder-wrap {
  cursor: default;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-sub);
  font-size: 12px;
}

.placeholder-state.error-state {
  color: var(--color-error, #ff4d4f);
}

.result-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  transition: transform 0.3s;
}

.result-image-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-main);
  font-weight: 600;
  transition: opacity 0.2s;
  pointer-events: none;
}

.regenerating-overlay {
  flex-direction: column;
  background: var(--bg-active);
  backdrop-filter: blur(2px);
  z-index: 10;
  pointer-events: auto;
}

.hover-overlay {
  background: linear-gradient(
    180deg,
    rgba(0, 0, 0, 0.05) 0%,
    rgba(0, 0, 0, 0.4) 100%
  );
  opacity: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-zoom-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  transform: scale(0.8) translateY(10px);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.image-card:hover .glass-zoom-icon {
  transform: scale(1) translateY(0);
}

.overlay-text {
  margin-top: 8px;
  font-size: 12px;
  color: var(--primary);
  font-weight: 600;
}

.overlay-regenerate-btn {
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  pointer-events: auto;
}

.overlay-regenerate-btn svg {
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.overlay-regenerate-btn:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

.overlay-regenerate-btn:hover svg {
  transform: rotate(180deg);
}

.overlay-regenerate-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.floating-regenerate-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 12;
}

.result-image-footer {
  padding: 14px 16px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-page-info {
  font-size: 13px;
  color: var(--text-sub);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.footer-page-info i {
  font-style: normal;
  opacity: 0.8;
}

.pill-download-btn {
  border: none;
  background: var(--primary-light, rgba(255, 36, 66, 0.08));
  color: var(--primary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 32px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.pill-download-btn:hover {
  background: var(--primary);
  color: #fff;
  box-shadow: 0 4px 12px rgba(255, 36, 66, 0.3);
  transform: translateY(-2px);
}

.pill-download-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.image-action-btn {
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
  color: var(--text-main);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  font-size: 12px;
  transition: all 0.18s ease;
}

.image-action-btn:hover {
  border-color: var(--border-hover);
  background: var(--bg-hover);
}

.image-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.image-card:hover img {
  transform: scale(1.05);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.preview-modal {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.preview-image {
  max-width: min(1100px, 95vw);
  max-height: 90vh;
  object-fit: contain;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35);
}

.preview-close {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  color: #fff;
  background: rgba(255, 255, 255, 0.18);
}

.preview-close:hover {
  background: rgba(255, 255, 255, 0.28);
}

@media (max-width: 768px) {
  .floating-regenerate-btn {
    top: 8px;
    right: 8px;
    height: 30px;
    padding: 0 10px;
    font-size: 11px;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGeneratorStore } from "../stores/generator";
import {
  appendUrlParams,
  downloadHistoryZip,
  getImageJob,
  getImageUrl,
  getHistory,
  regenerateImage,
  updateHistory,
  withAccessToken,
} from "../api";
import ContentDisplay from "../components/result/ContentDisplay.vue";
import { useMessage } from "naive-ui";

const router = useRouter();
const route = useRoute();
const store = useGeneratorStore();
const message = useMessage();

const regeneratingIndex = ref<number | null>(null);
const errorText = ref("");
const pollingActive = ref(false);
const previewVisible = ref(false);
const previewImageUrl = ref("");
let stopPolling = false;

const doneCount = computed(
  () => store.images.filter((img) => img.status === "done" && !!img.url).length,
);
const failedCount = computed(
  () => store.images.filter((img) => img.status === "error").length,
);
const isGenerating = computed(
  () => store.progress.status === "generating" && !!store.imageJobId,
);
const progressPercent = computed(() => {
  if (store.progress.total <= 0) return 0;
  return (store.progress.current / store.progress.total) * 100;
});
const canPublish = computed(() => {
  if (isGenerating.value) return false;
  return (
    store.images.length > 0 &&
    store.images.every((img) => img.status === "done" && !!img.url)
  );
});

const openPreview = (url: string) => {
  const baseUrl = url.split("?")[0];
  previewImageUrl.value = appendUrlParams(withAccessToken(baseUrl), {
    thumbnail: false,
  });
  previewVisible.value = true;
};

const closePreview = () => {
  previewVisible.value = false;
  previewImageUrl.value = "";
};

const onPreviewKeydown = (event: KeyboardEvent) => {
  if (event.key === "Escape" && previewVisible.value) {
    closePreview();
  }
};

const startOver = () => {
  store.reset();
  router.push("/");
};

const goToPublish = () => {
  if (!canPublish.value) {
    message.warning("图片仍在生成或存在失败，暂不可发布");
    return;
  }
  router.push("/redbook/publish");
};

const downloadOne = (image: any) => {
  if (!image.url) return;
  const link = document.createElement("a");
  const baseUrl = image.url.split("?")[0];
  link.href = appendUrlParams(withAccessToken(baseUrl), { thumbnail: false });
  link.download = `rednote_page_${image.index + 1}.png`;
  link.click();
};

function hasPersistableContent() {
  const hasTitles =
    Array.isArray(store.content.titles) &&
    store.content.titles.some((t) => String(t || "").trim());
  const hasCopywriting = Boolean(
    String(store.content.copywriting || "").trim(),
  );
  const hasTags =
    Array.isArray(store.content.tags) &&
    store.content.tags.some((t) => String(t || "").trim());
  return hasTitles || hasCopywriting || hasTags;
}

async function syncContentToHistory() {
  if (!store.recordId || !hasPersistableContent()) return;
  try {
    await updateHistory(store.recordId, {
      content: {
        titles: [...(store.content.titles || [])],
        copywriting: String(store.content.copywriting || ""),
        tags: [...(store.content.tags || [])],
      },
    });
  } catch (error) {
    console.error("下载前同步文案到历史记录失败:", error);
  }
}

const downloadAll = async () => {
  if (isGenerating.value) {
    message.warning("图片仍在生成中，请稍后再下载");
    return;
  }

  if (store.recordId) {
    await syncContentToHistory();

    const fallbackLink = document.createElement("a");
    fallbackLink.href = appendUrlParams(
      withAccessToken(`/api/history/${store.recordId}/download`),
      { _: Date.now() },
    );

    try {
      const contentPayload = hasPersistableContent()
        ? {
            titles: [...(store.content.titles || [])],
            copywriting: String(store.content.copywriting || ""),
            tags: [...(store.content.tags || [])],
          }
        : undefined;

      const { blob, filename } = await downloadHistoryZip(
        store.recordId,
        contentPayload,
      );
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("打包下载失败，回退到直链下载:", error);
      fallbackLink.click();
    }
    return;
  }

  store.images.forEach((image, index) => {
    if (!image.url) return;
    setTimeout(() => {
      const link = document.createElement("a");
      const baseUrl = image.url.split("?")[0];
      link.href = appendUrlParams(withAccessToken(baseUrl), {
        thumbnail: false,
      });
      link.download = `rednote_page_${image.index + 1}.png`;
      link.click();
    }, index * 300);
  });
};

async function syncImageStateToHistory(taskId: string) {
  if (!store.recordId) return;
  try {
    const generated = store.outline.pages.map((p) => {
      const img = store.images.find((i) => i.index === p.index);
      if (img && img.status === "done" && img.url) {
        return img.url.split("/").pop()?.split("?")[0] || "";
      }
      return "";
    });

    const completedCount = generated.filter((name) => name !== "").length;
    let status = "completed";
    if (failedCount.value > 0) {
      status = completedCount > 0 ? "partial" : "draft";
    }

    const firstPage = store.images.find((img) => img.index === 0);
    const thumbnail =
      firstPage && firstPage.status === "done" && firstPage.url
        ? firstPage.url.split("/").pop()?.split("?")[0]
        : generated.find((name) => name !== "") || null;

    await updateHistory(store.recordId, {
      images: {
        task_id: taskId,
        generated,
      },
      status,
      thumbnail: thumbnail || undefined,
    });
  } catch (e) {
    console.error("同步图片状态到历史记录失败:", e);
  }
}

const handleRegenerate = async (image: any) => {
  if (!store.taskId || regeneratingIndex.value !== null || isGenerating.value)
    return;

  regeneratingIndex.value = image.index;
  try {
    const pageContent = store.outline.pages.find(
      (p) => p.index === image.index,
    );
    if (!pageContent) {
      message.warning("无法找到对应页面内容");
      return;
    }

    const context = {
      fullOutline: store.outline.raw || "",
      userTopic: store.topic || "",
      userPrompt: store.imagePrompt.userPrompt || "",
      systemPrompt: store.imagePrompt.systemPrompt || "",
    };

    const result = await regenerateImage(
      store.taskId,
      pageContent,
      true,
      context,
    );
    if (result.success && result.image_url) {
      store.updateImage(image.index, result.image_url);
      await syncImageStateToHistory(store.taskId);
    } else {
      message.error("重绘失败: " + (result.error || "未知错误"));
    }
  } catch (e: any) {
    message.error("重绘失败: " + e.message);
  } finally {
    regeneratingIndex.value = null;
  }
};

function resolveRouteRecordId() {
  const queryId =
    typeof route.query.recordId === "string" ? route.query.recordId.trim() : "";
  if (queryId) return queryId;
  const paramId =
    typeof route.params.recordId === "string"
      ? route.params.recordId.trim()
      : "";
  return paramId;
}

async function hydrateFromHistoryRecord(recordId: string) {
  const res = await getHistory(recordId);
  if (!res.success || !res.record) {
    message.error("无法加载结果页：历史记录不存在或已被删除");
    router.push("/history");
    return;
  }

  const record = res.record;
  store.setTopic(record.title);
  store.setOutline(record.outline.raw, record.outline.pages);
  store.setRecordId(record.id);
  store.imageJobId = null;

  if (record.content) {
    store.setContent(
      record.content.titles || [],
      record.content.copywriting || "",
      record.content.tags || [],
    );
  } else {
    store.clearContent();
  }

  const taskId = record.images?.task_id || null;
  const generated = Array.isArray(record.images?.generated)
    ? record.images.generated
    : [];
  store.taskId = taskId;

  if (taskId) {
    store.images = record.outline.pages.map((_, idx) => {
      const filename = generated[idx];
      return {
        index: idx,
        url: filename ? getImageUrl(taskId, filename) : "",
        status: filename ? "done" : "error",
        retryable: !filename,
      };
    });
    store.finishGeneration(taskId);
  } else {
    store.images = [];
    store.stage = "result";
  }
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollImageJobUntilFinished(jobId: string): Promise<{
  taskId: string;
  status: "success" | "failed" | "cancelled";
}> {
  const seenSuccess = new Set<number>();
  const seenFailed = new Set<number>();
  let finalTaskId = store.taskId || `task_${Date.now()}_job`;
  let consecutiveErrors = 0;

  while (!stopPolling) {
    const result = await getImageJob(jobId);
    if (!result.success || !result.data) {
      consecutiveErrors += 1;
      if (consecutiveErrors >= 5) {
        throw new Error(result.error || "轮询图片任务失败");
      }
      await sleep(1200);
      continue;
    }

    consecutiveErrors = 0;
    const job = result.data;
    const items = Array.isArray(job.items) ? job.items : [];
    for (const item of items) {
      const index = Number(item.page_index);
      if (!Number.isFinite(index) || index < 0) continue;

      if (
        item.status === "success" &&
        !seenSuccess.has(index) &&
        item.image_url
      ) {
        seenSuccess.add(index);
        seenFailed.delete(index);
        store.updateProgress(index, "done", item.image_url);
      } else if (
        item.status === "failed" &&
        !seenFailed.has(index) &&
        !seenSuccess.has(index)
      ) {
        seenFailed.add(index);
        store.updateProgress(
          index,
          "error",
          undefined,
          item.error || "生成失败",
        );
      }
    }

    const candidateTaskId =
      String(job.task_id || "") || String((job.result as any)?.task_id || "");
    if (candidateTaskId) {
      finalTaskId = candidateTaskId;
    }

    if (
      job.status === "success" ||
      job.status === "failed" ||
      job.status === "cancelled"
    ) {
      store.finishGeneration(finalTaskId);
      return {
        taskId: finalTaskId,
        status: job.status,
      };
    }

    await sleep(1000);
  }

  return {
    taskId: finalTaskId,
    status: "cancelled",
  };
}

async function startPollingIfNeeded() {
  if (!store.imageJobId || pollingActive.value) return;
  pollingActive.value = true;
  errorText.value = "";

  try {
    const finished = await pollImageJobUntilFinished(store.imageJobId);
    if (finished.status === "cancelled") {
      errorText.value = "图片任务已取消";
      store.progress.status = "error";
      return;
    }
    await syncImageStateToHistory(finished.taskId);
  } catch (err: any) {
    errorText.value = "图片轮询失败: " + (err?.message || String(err));
    store.progress.status = "error";
  } finally {
    pollingActive.value = false;
  }
}

onMounted(async () => {
  const recordId = resolveRouteRecordId();
  if (recordId) {
    await hydrateFromHistoryRecord(recordId);
    return;
  }

  if (store.outline.pages.length === 0) {
    router.push("/");
    return;
  }

  await startPollingIfNeeded();
});

onMounted(() => {
  window.addEventListener("keydown", onPreviewKeydown);
});

onUnmounted(() => {
  stopPolling = true;
  window.removeEventListener("keydown", onPreviewKeydown);
  closePreview();
});
</script>
