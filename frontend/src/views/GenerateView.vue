<template>
  <div class="container launch-page">
    <div class="card launch-card">
      <h1 class="page-title">准备生成</h1>
      <p class="page-subtitle" v-if="!errorText">
        正在创建图片任务，即将进入结果页并并行生成图片与文案...
      </p>

      <div v-if="!errorText" class="launch-loading">
        <div class="spinner"></div>
      </div>

      <div v-else class="launch-error">
        <p>{{ errorText }}</p>
        <div class="actions">
          <button class="btn btn-primary" @click="launch" :disabled="launching">
            重试
          </button>
          <button class="btn" @click="router.push('/redbook/outline')">
            返回大纲
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useGeneratorStore } from "../stores/generator";
import { createHistory, createImageJob, updateHistory } from "../api";

const router = useRouter();
const store = useGeneratorStore();

const launching = ref(false);
const errorText = ref("");

async function ensureHistoryRecord() {
  if (store.recordId) {
    await updateHistory(store.recordId, { status: "generating" });
    return;
  }

  const result = await createHistory(store.topic, {
    raw: store.outline.raw,
    pages: store.outline.pages,
  });
  if (result.success && result.record_id) {
    store.setRecordId(result.record_id);
  }
}

async function launch() {
  if (launching.value) return;
  launching.value = true;
  errorText.value = "";

  try {
    if (store.outline.pages.length === 0) {
      router.push("/");
      return;
    }

    await ensureHistoryRecord();

    store.startGeneration();
    const pagesToGenerate = store.outline.pages.filter((page) => {
      const existing = store.images.find((img) => img.index === page.index);
      return !existing || existing.status !== "done" || !existing.url;
    });

    if (pagesToGenerate.length === 0) {
      if (!store.taskId) {
        store.taskId = `task_${Date.now()}_existing`;
      }
      store.imageJobId = null;
      store.finishGeneration(store.taskId);
      router.replace("/redbook/result");
      return;
    }

    const createResult = await createImageJob(
      pagesToGenerate,
      store.taskId,
      store.outline.raw,
      store.userImages.length > 0 ? store.userImages : undefined,
      store.topic,
      {
        userPrompt: store.imagePrompt.userPrompt || "",
        systemPrompt: store.imagePrompt.systemPrompt || "",
      },
    );

    if (!createResult.success || !createResult.job_id) {
      throw new Error(createResult.error || "创建图片任务失败");
    }

    store.imageJobId = createResult.job_id;
    router.replace("/redbook/result");
  } catch (err: any) {
    store.progress.status = "error";
    errorText.value = "生成任务创建失败: " + (err?.message || String(err));
  } finally {
    launching.value = false;
  }
}

onMounted(() => {
  launch();
});
</script>

<style scoped>
.launch-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
}

.launch-card {
  width: min(680px, 100%);
  text-align: center;
  padding: 40px 28px;
}

.launch-loading {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

.launch-error {
  margin-top: 16px;
  color: var(--color-error, #ff4d4f);
}

.actions {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
