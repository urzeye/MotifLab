<template>
  <div class="container">
    <div class="page-header">
      <div>
        <h1 class="page-title">生成结果</h1>
        <p class="page-subtitle">
          <span v-if="isGenerating"
            >正在生成第 {{ store.progress.current + 1 }} /
            {{ store.progress.total }} 页</span
          >
          <span v-else-if="hasFailedImages"
            >{{ failedCount }} 张图片生成失败，可点击重试</span
          >
          <span v-else>全部 {{ store.progress.total }} 张图片生成完成</span>
        </p>
      </div>
      <div style="display: flex; gap: 10px">
        <button
          v-if="hasFailedImages && !isGenerating"
          class="btn btn-primary"
          @click="retryAllFailed"
          :disabled="isRetrying"
        >
          {{ isRetrying ? "补全中..." : "一键补全失败图片" }}
        </button>
        <button
          class="btn"
          @click="router.push('/redbook/outline')"
          style="border: 1px solid var(--border-color)"
        >
          返回大纲
        </button>
      </div>
    </div>

    <div class="card">
      <div
        style="
          margin-bottom: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        "
      >
        <span style="font-weight: 600">生成进度</span>
        <span style="color: var(--primary); font-weight: 600"
          >{{ Math.round(progressPercent) }}%</span
        >
      </div>
      <div class="progress-container">
        <div
          class="progress-bar"
          :style="{ width: progressPercent + '%' }"
        />
      </div>

      <div
        v-if="error"
        class="error-msg"
      >
        {{ error }}
      </div>

      <div
        class="grid-cols-4"
        style="margin-top: 40px"
      >
        <div
          v-for="image in store.images"
          :key="image.index"
          class="image-card"
        >
          <!-- 图片展示区域 -->
          <div
            v-if="image.url && image.status === 'done'"
            class="image-preview"
          >
            <img
              :src="resolveImageUrl(image)"
              @error="handleImageError(image)"
              :alt="`第 ${image.index + 1} 页`"
            />
            <!-- 重新生成按钮（悬停显示） -->
            <div class="image-overlay">
              <button
                class="overlay-btn"
                @click="regenerateImage(image.index)"
                :disabled="false"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M23 4v6h-6"></path>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                重新生成
              </button>
            </div>
          </div>

          <!-- 生成中/重试中状态 -->
          <div
            v-else-if="
              image.status === 'generating' || image.status === 'retrying'
            "
            class="image-placeholder"
          >
            <div class="spinner"></div>
            <div class="status-text">
              {{ image.status === "retrying" ? "重试中..." : "生成中..." }}
            </div>
          </div>

          <!-- 失败状态 -->
          <div
            v-else-if="image.status === 'error'"
            class="image-placeholder error-placeholder"
          >
            <div class="error-icon">!</div>
            <div class="status-text">生成失败</div>
            <button
              class="retry-btn"
              @click="retrySingleImage(image.index)"
              :disabled="isRetrying"
            >
              点击重试
            </button>
          </div>

          <!-- 等待中状态 -->
          <div
            v-else
            class="image-placeholder"
          >
            <div class="status-text">等待中</div>
          </div>

          <!-- 底部信息栏 -->
          <div class="image-footer">
            <span class="page-label">Page {{ image.index + 1 }}</span>
            <span
              class="status-badge"
              :class="image.status"
            >
              {{ getStatusText(image.status) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useGeneratorStore } from "../stores/generator";
import {
  generateImagesPost,
  regenerateImage as apiRegenerateImage,
  retryFailedImages as apiRetryFailed,
  createHistory,
  updateHistory,
} from "../api";

const router = useRouter();
const store = useGeneratorStore();

const error = ref("");
const isRetrying = ref(false);

const isGenerating = computed(() => store.progress.status === "generating");

const progressPercent = computed(() => {
  if (store.progress.total === 0) return 0;
  return (store.progress.current / store.progress.total) * 100;
});

const hasFailedImages = computed(() =>
  store.images.some((img) => img.status === "error"),
);

const failedCount = computed(
  () => store.images.filter((img) => img.status === "error").length,
);

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    generating: "生成中",
    done: "已完成",
    error: "失败",
    retrying: "重试中",
  };
  return texts[status] || "等待中";
};

// 重试单张图片（异步并发执行，不阻塞）
// 记录加载失败的缩略图索引，失败后回退原图
const failedThumbs = ref(new Set<number>());

function resolveImageUrl(image: { index: number; url?: string }) {
  const rawUrl = image.url || "";
  if (!rawUrl) return rawUrl;

  if (failedThumbs.value.has(image.index)) {
    const sep = rawUrl.includes("?") ? "&" : "?";
    return rawUrl + sep + "thumbnail=false&retry=" + Date.now();
  }

  return rawUrl;
}

function handleImageError(image: { index: number }) {
  if (!failedThumbs.value.has(image.index)) {
    console.warn("第 " + (image.index + 1) + " 页缩略图加载失败，尝试加载原图");
    failedThumbs.value.add(image.index);
  }
}

function retrySingleImage(index: number) {
  if (!store.taskId) return;

  const page = store.outline.pages.find((p) => p.index === index);
  if (!page) return;

  // 立即设置为重试状态
  store.setImageRetrying(index);

  // 构建上下文信息
  const context = {
    fullOutline: store.outline.raw || "",
    userTopic: store.topic || "",
  };

  // 异步执行重绘，不阻塞
  apiRegenerateImage(store.taskId, page, true, context)
    .then((result) => {
      if (result.success && result.image_url) {
        store.updateImage(index, result.image_url);
      } else {
        store.updateProgress(index, "error", undefined, result.error);
      }
    })
    .catch((e) => {
      store.updateProgress(index, "error", undefined, String(e));
    });
}

// 重新生成图片（成功的也可以重新生成，立即返回不等待）
function regenerateImage(index: number) {
  retrySingleImage(index);
}

// 批量重试所有失败的图片
async function retryAllFailed() {
  if (!store.taskId) return;

  const failedPages = store.getFailedPages();
  if (failedPages.length === 0) return;

  isRetrying.value = true;

  // 设置所有失败的图片为重试状态
  failedPages.forEach((page) => {
    store.setImageRetrying(page.index);
  });

  try {
    await apiRetryFailed(
      store.taskId,
      failedPages,
      // onProgress
      () => {},
      // onComplete
      (event) => {
        if (event.image_url) {
          store.updateImage(event.index, event.image_url);
        }
      },
      // onError
      (event) => {
        store.updateProgress(event.index, "error", undefined, event.message);
      },
      // onFinish
      () => {
        isRetrying.value = false;
      },
      // onStreamError
      (err) => {
        console.error("重试失败:", err);
        isRetrying.value = false;
        error.value = "重试失败: " + err.message;
      },
    );
  } catch (e) {
    isRetrying.value = false;
    error.value = "重试失败: " + String(e);
  }
}

onMounted(async () => {
  if (store.outline.pages.length === 0) {
    router.push("/");
    return;
  }

  // 历史记录处理逻辑：
  // 正常情况下，recordId 应该在大纲生成页（OutlineView）创建
  // 这里根据 recordId 是否存在做不同处理
  if (store.recordId) {
    // 情况1：recordId 已存在（正常流程）
    // 更新历史记录状态为 generating，表示图片生成已开始
    try {
      await updateHistory(store.recordId, { status: "generating" });
      console.log("历史记录状态已更新为 generating:", store.recordId);
    } catch (e) {
      // 更新失败不阻断生成流程，仅记录错误
      console.error("更新历史记录状态失败:", e);
    }
  } else {
    // 情况2：recordId 不存在（异常情况）
    // 这种情况不应该发生，但作为兜底逻辑，尝试创建历史记录
    console.warn("警告: recordId 不存在，尝试创建历史记录作为兜底");
    try {
      const result = await createHistory(store.topic, {
        raw: store.outline.raw,
        pages: store.outline.pages,
      });
      if (result.success && result.record_id) {
        store.setRecordId(result.record_id);
        console.log("兜底创建历史记录成功:", store.recordId);
      }
    } catch (e) {
      // 创建失败也不阻断生成流程，仅记录错误
      console.error("兜底创建历史记录失败:", e);
    }
  }

  store.startGeneration();
  const pagesToGenerate = store.outline.pages.filter((page) => {
    const existing = store.images.find((img) => img.index === page.index);
    return !existing || existing.status !== "done" || !existing.url;
  });

  // 所有页面都已生成时，直接进入结果页
  if (pagesToGenerate.length === 0) {
    if (!store.taskId) {
      store.taskId = `task_${Date.now()}_existing`;
    }
    store.finishGeneration(store.taskId);
    router.push("/redbook/result");
    return;
  }

  generateImagesPost(
    pagesToGenerate,
    store.taskId,
    store.outline.raw, // 传入完整大纲文本
    // onProgress
    (event) => {
      console.log("Progress:", event);
    },
    // onComplete
    (event) => {
      console.log("Complete:", event);
      if (event.image_url) {
        store.updateProgress(event.index, "done", event.image_url);
      }
    },
    // onError
    (event) => {
      console.error("Error:", event);
      store.updateProgress(event.index, "error", undefined, event.message);
    },
    // onFinish
    async (event) => {
      console.log("Finish:", event);
      store.finishGeneration(event.task_id);

      // 更新历史记录
      if (store.recordId) {
        try {
          // 构建完整列表：保留已完成图片，未完成位置保持空字符串
          const generatedImages = store.outline.pages.map((p) => {
            const img = store.images.find((i) => i.index === p.index);
            if (img && img.status === "done" && img.url) {
              return img.url.split("/").pop()?.split("?")[0] || "";
            }
            return "";
          });
          const completedCount = generatedImages.filter(
            (name) => name !== "",
          ).length;

          // 确定状态
          let status = "completed";
          if (hasFailedImages.value) {
            status = completedCount > 0 ? "partial" : "draft";
          }

          // 优先使用第一页图片作为缩略图
          const firstPage = store.images.find((img) => img.index === 0);
          const thumbnail =
            firstPage && firstPage.status === "done" && firstPage.url
              ? firstPage.url.split("/").pop()?.split("?")[0]
              : generatedImages.find((name) => name !== "") || null;

          await updateHistory(store.recordId, {
            images: {
              task_id: event.task_id,
              generated: generatedImages,
            },
            status: status,
            thumbnail: thumbnail || undefined,
          });
          console.log("历史记录已更新");
        } catch (e) {
          console.error("更新历史记录失败:", e);
        }
      }

      // 如果没有失败的，跳转到结果页
      if (!hasFailedImages.value) {
        setTimeout(() => {
          router.push("/redbook/result");
        }, 1000);
      }
    },
    // onStreamError
    (err) => {
      console.error("Stream Error:", err);
      error.value = "生成失败: " + err.message;
    },
    // userImages - 用户上传的参考图片
    store.userImages.length > 0 ? store.userImages : undefined,
    // userTopic - 用户原始输入
    store.topic,
  );
});
</script>

<style scoped>
.image-preview {
  aspect-ratio: 3/4;
  overflow: hidden;
  position: relative;
  flex: 1; /* 填充卡片剩余空间 */
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.image-preview:hover .image-overlay {
  opacity: 1;
}

.overlay-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-main);
  transition: all 0.2s;
}

.overlay-btn:hover {
  background: var(--primary);
  color: var(--text-on-primary, white);
}

.overlay-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.image-placeholder {
  aspect-ratio: 3/4;
  background: var(--bg-elevated);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex: 1; /* 填充卡片剩余空间 */
  min-height: 240px; /* 确保有最小高度 */
}

.error-placeholder {
  background: var(--color-error-bg);
}

.error-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-error, #ff4d4f);
  color: var(--text-on-primary, white);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
}

.status-text {
  font-size: 13px;
  color: var(--text-sub);
}

.retry-btn {
  margin-top: 8px;
  padding: 6px 16px;
  background: var(--primary);
  color: var(--text-on-primary, white);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.retry-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.image-footer {
  padding: 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-label {
  font-size: 12px;
  color: var(--text-sub);
}

.status-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
}

.status-badge.done {
  background: var(--color-success-bg, #e6f7ed);
  color: var(--color-success, #52c41a);
}

.status-badge.generating,
.status-badge.retrying {
  background: var(--color-info-bg, #e6f4ff);
  color: var(--color-info, #1890ff);
}

.status-badge.error {
  background: var(--color-error-bg, #fff1f0);
  color: var(--color-error, #ff4d4f);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
