<template>
  <div class="container">
    <div class="page-header">
      <div>
        <h1 class="page-title">发布到小红书</h1>
        <p class="page-subtitle">将生成的内容发布到小红书平台</p>
      </div>
      <div style="display: flex; gap: 12px;">
        <button class="btn" @click="goBack" style="background: white; border: 1px solid var(--border-color);">
          返回结果
        </button>
      </div>
    </div>

    <!-- VibeSurf 状态检测 -->
    <div class="card" style="margin-bottom: 24px;">
      <div style="display: flex; align-items: center; gap: 16px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <div
            :style="{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: vibeSurfStatus?.running ? 'var(--primary)' : '#ef4444'
            }"
          ></div>
          <span style="font-weight: 600;">VibeSurf 服务</span>
        </div>
        <span style="color: var(--text-sub); font-size: 14px;">
          {{ vibeSurfStatus?.message || '检测中...' }}
        </span>
        <button
          v-if="!vibeSurfStatus?.running"
          class="btn"
          style="margin-left: auto; padding: 8px 16px; font-size: 14px;"
          @click="checkVibeSurf"
        >
          重新检测
        </button>
      </div>
    </div>

    <!-- 登录状态检测 -->
    <div v-if="vibeSurfStatus?.running" class="card" style="margin-bottom: 24px;">
      <div style="display: flex; align-items: center; gap: 16px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <div
            :style="{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: loginStatus?.logged_in ? 'var(--primary)' : '#f59e0b'
            }"
          ></div>
          <span style="font-weight: 600;">小红书登录状态</span>
        </div>
        <span style="color: var(--text-sub); font-size: 14px;">
          {{ loginStatus?.message || '检测中...' }}
        </span>
        <button
          v-if="!loginStatus?.logged_in"
          class="btn btn-primary"
          style="margin-left: auto; padding: 8px 16px; font-size: 14px;"
          @click="openLogin"
          :disabled="openingLogin"
        >
          {{ openingLogin ? '打开中...' : '登录小红书' }}
        </button>
        <button
          class="btn"
          style="padding: 8px 16px; font-size: 14px;"
          @click="checkLogin"
        >
          刷新状态
        </button>
      </div>
    </div>

    <!-- 内容预览 -->
    <div v-if="vibeSurfStatus?.running && store.images.length > 0" class="card">
      <h2 style="font-size: 18px; font-weight: 600; margin-bottom: 20px;">发布预览</h2>

      <!-- 图片预览 -->
      <div style="margin-bottom: 24px;">
        <h3 style="font-size: 14px; color: var(--text-sub); margin-bottom: 12px;">图片 ({{ store.images.length }} 张)</h3>
        <div style="display: flex; gap: 12px; overflow-x: auto; padding-bottom: 12px;">
          <div
            v-for="image in store.images"
            :key="image.index"
            style="flex-shrink: 0; width: 120px; height: 160px; border-radius: 8px; overflow: hidden; border: 1px solid var(--border-color);"
          >
            <img
              :src="image.url"
              :alt="`第 ${image.index + 1} 页`"
              style="width: 100%; height: 100%; object-fit: cover;"
            />
          </div>
        </div>
      </div>

      <!-- 标题 -->
      <div style="margin-bottom: 20px;">
        <h3 style="font-size: 14px; color: var(--text-sub); margin-bottom: 8px;">标题</h3>
        <select
          v-model="selectedTitle"
          style="width: 100%; padding: 12px; border: 1px solid var(--border-color); border-radius: 8px; font-size: 16px;"
        >
          <option v-for="(title, idx) in store.content.titles" :key="idx" :value="title">
            {{ title }}
          </option>
        </select>
      </div>

      <!-- 正文 -->
      <div style="margin-bottom: 20px;">
        <h3 style="font-size: 14px; color: var(--text-sub); margin-bottom: 8px;">正文</h3>
        <textarea
          v-model="copywriting"
          rows="6"
          style="width: 100%; padding: 12px; border: 1px solid var(--border-color); border-radius: 8px; font-size: 14px; resize: vertical;"
        ></textarea>
      </div>

      <!-- 标签 -->
      <div style="margin-bottom: 24px;">
        <h3 style="font-size: 14px; color: var(--text-sub); margin-bottom: 8px;">标签</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
          <span
            v-for="(tag, idx) in store.content.tags"
            :key="idx"
            style="padding: 6px 12px; background: var(--bg-secondary); border-radius: 16px; font-size: 13px;"
          >
            #{{ tag }}
          </span>
        </div>
      </div>

      <!-- 发布按钮 -->
      <div style="display: flex; gap: 12px;">
        <button
          class="btn btn-primary"
          style="flex: 1; padding: 14px; font-size: 16px;"
          :disabled="!canPublish || isPublishing"
          @click="startPublish"
        >
          {{ isPublishing ? '发布中...' : '确认发布' }}
        </button>
      </div>

      <!-- 发布进度 -->
      <div v-if="isPublishing && publishProgress.length > 0" style="margin-top: 24px; border-top: 1px solid var(--border-color); padding-top: 20px;">
        <h3 style="font-size: 14px; color: var(--text-sub); margin-bottom: 12px;">发布进度</h3>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <div
            v-for="(step, idx) in publishProgress"
            :key="idx"
            style="display: flex; align-items: center; gap: 12px; padding: 12px; background: var(--bg-secondary); border-radius: 8px;"
          >
            <div
              :style="{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                background: step.success === true ? 'var(--primary)' : step.success === false ? '#ef4444' : 'var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '12px'
              }"
            >
              <span v-if="step.success === true">✓</span>
              <span v-else-if="step.success === false">✗</span>
              <span v-else>{{ idx + 1 }}</span>
            </div>
            <div style="flex: 1;">
              <div style="font-weight: 500;">{{ step.step }}</div>
              <div style="font-size: 13px; color: var(--text-sub);">{{ step.message }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 发布结果 -->
      <div v-if="publishResult" style="margin-top: 24px; border-top: 1px solid var(--border-color); padding-top: 20px;">
        <div
          :style="{
            padding: '16px',
            borderRadius: '8px',
            background: publishResult.success ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'
          }"
        >
          <div style="font-weight: 600; margin-bottom: 8px;">
            {{ publishResult.success ? '发布成功!' : '发布失败' }}
          </div>
          <div v-if="publishResult.post_url" style="font-size: 14px;">
            <a :href="publishResult.post_url" target="_blank" style="color: var(--primary);">
              查看已发布的笔记
            </a>
          </div>
          <div v-if="publishResult.error" style="font-size: 14px; color: #ef4444;">
            {{ publishResult.error }}
          </div>
        </div>
      </div>
    </div>

    <!-- 无内容提示 -->
    <div v-else-if="store.images.length === 0" class="card">
      <div style="text-align: center; padding: 48px 24px; color: var(--text-sub);">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 16px;">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
        <p style="font-size: 16px; margin-bottom: 16px;">还没有生成内容</p>
        <button class="btn btn-primary" @click="goHome">去生成</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import {
  checkVibeSurfStatus,
  checkXiaohongshuLogin,
  openXiaohongshuLogin,
  publishToXiaohongshu,
  type VibeSurfStatus,
  type LoginStatus,
  type PublishProgressEvent
} from '../api'

const router = useRouter()
const store = useGeneratorStore()

// 状态
const vibeSurfStatus = ref<VibeSurfStatus | null>(null)
const loginStatus = ref<LoginStatus | null>(null)
const openingLogin = ref(false)
const isPublishing = ref(false)
const publishProgress = ref<PublishProgressEvent[]>([])
const publishResult = ref<{ success: boolean; post_url?: string; error?: string } | null>(null)

// 表单数据
const selectedTitle = ref('')
const copywriting = ref('')

// 计算属性
const canPublish = computed(() => {
  return vibeSurfStatus.value?.running &&
         loginStatus.value?.logged_in &&
         store.images.length > 0 &&
         selectedTitle.value &&
         copywriting.value
})

// 方法
const goBack = () => {
  router.push('/redbook/result')
}

const goHome = () => {
  router.push('/')
}

const checkVibeSurf = async () => {
  try {
    const result = await checkVibeSurfStatus()
    if (result.success && result.status) {
      vibeSurfStatus.value = result.status
      if (result.status.running) {
        checkLogin()
      }
    } else {
      vibeSurfStatus.value = { running: false, message: result.error || '检测失败' }
    }
  } catch (e: any) {
    vibeSurfStatus.value = { running: false, message: e.message }
  }
}

const checkLogin = async () => {
  try {
    const result = await checkXiaohongshuLogin()
    if (result.success && result.status) {
      loginStatus.value = result.status
    } else {
      loginStatus.value = { logged_in: false, message: result.error || '检测失败' }
    }
  } catch (e: any) {
    loginStatus.value = { logged_in: false, message: e.message }
  }
}

const openLogin = async () => {
  openingLogin.value = true
  try {
    const result = await openXiaohongshuLogin()
    if (!result.success) {
      alert('打开登录页面失败: ' + result.error)
    }
  } catch (e: any) {
    alert('打开登录页面失败: ' + e.message)
  } finally {
    openingLogin.value = false
  }
}

const startPublish = async () => {
  if (!canPublish.value) return

  isPublishing.value = true
  publishProgress.value = []
  publishResult.value = null

  const imageUrls = store.images.map(img => img.url)

  publishToXiaohongshu(
    {
      images: imageUrls,
      title: selectedTitle.value,
      content: copywriting.value,
      tags: store.content.tags
    },
    // onProgress
    (event: PublishProgressEvent) => {
      publishProgress.value.push(event)
    },
    // onComplete
    (event: PublishProgressEvent) => {
      isPublishing.value = false
      publishResult.value = {
        success: event.success || false,
        post_url: event.post_url,
        error: event.error
      }
    },
    // onError
    (event: PublishProgressEvent) => {
      isPublishing.value = false
      publishResult.value = {
        success: false,
        error: event.error || '发布失败'
      }
    },
    // onStreamError
    (error: Error) => {
      isPublishing.value = false
      publishResult.value = {
        success: false,
        error: error.message
      }
    }
  )
}

// 初始化
onMounted(() => {
  // 初始化表单数据
  if (store.content.titles.length > 0) {
    selectedTitle.value = store.content.titles[0]
  }
  copywriting.value = store.content.copywriting || ''

  // 检测 VibeSurf 状态
  checkVibeSurf()
})
</script>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
</style>
