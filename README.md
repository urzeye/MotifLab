<div align="center">

<img src="images/logo.png" alt="渲染AI" width="120"/>

# 渲染AI - 图文生成器

**让传播不再需要门槛，让创作从未如此简单**

输入你的创意主题，让 AI 帮你生成爆款标题、正文和封面图

</div>

---

## 效果展示

### 输入一句话，生成完整图文

<details open>
<summary><b>Step 1: 智能大纲生成</b></summary>

<br>

![大纲示例](./images/example-2.png)

**功能特性：**
- 可编辑每页内容
- 可调整页面顺序
- 自定义每页描述

</details>

<details open>
<summary><b>Step 2: 封面页生成</b></summary>

<br>

![封面示例](./images/example-3.png)

**封面亮点：**
- 符合个人风格
- 文字准确无误
- 视觉统一协调

</details>

<details open>
<summary><b>Step 3: 内容页批量生成</b></summary>

<br>

![内容页示例](./images/example-4.png)

**生成说明：**
- 并发生成所有页面（默认最多 15 张）
- 如 API 不支持高并发，请在设置中关闭
- 支持单独重新生成不满意的页面

</details>

---

## 技术架构

<table>
<tr>
<td width="50%" valign="top">

### 后端技术栈

| 技术 | 说明 |
|------|------|
| **语言** | Python 3.9+ |
| **框架** | Flask |
| **文案AI** | Gemini / OpenAI |
| **图片AI** | Google GenAI |

</td>
<td width="50%" valign="top">

### 前端技术栈

| 技术 | 说明 |
|------|------|
| **框架** | Vue 3 + TypeScript |
| **构建工具** | Vite |
| **状态管理** | Pinia |
| **样式** | Modern CSS |

</td>
</tr>
</table>

---

## 快速开始

### 前置要求
- Python 3.9+
- Node.js 18+
- npm

### 1. 克隆项目
```bash
git clone https://github.com/joshua23/renderink-xiaohongshu.git
cd renderink-xiaohongshu
```

### 2. 配置 API 服务

复制配置模板文件：
```bash
cp text_providers.yaml.example text_providers.yaml
cp image_providers.yaml.example image_providers.yaml
```

编辑配置文件，填入你的 API Key。也可以启动后在 Web 界面的**设置页面**进行配置。

### 3. 一键启动

```bash
./start.sh
```

启动后自动打开浏览器访问 http://localhost:5173

---

## 配置说明

### 文本生成配置

配置文件: `text_providers.yaml`

```yaml
# 当前激活的服务商
active_provider: gemini

providers:
  # Google Gemini（原生接口）
  gemini:
    type: google_gemini
    api_key: AIzaxxxxxxxxxxxxxxxxxxxxxxxxx
    model: gemini-2.0-flash

  # OpenAI 兼容接口
  openai:
    type: openai_compatible
    api_key: sk-xxxxxxxxxxxxxxxxxxxx
    base_url: https://api.openai.com/v1
    model: gpt-4o
```

### 图片生成配置

配置文件: `image_providers.yaml`

```yaml
# 当前激活的服务商
active_provider: gemini

providers:
  # Google Gemini 图片生成
  gemini:
    type: google_genai
    api_key: AIzaxxxxxxxxxxxxxxxxxxxxxxxxx
    model: gemini-3-pro-image-preview
    high_concurrency: false
```

### 高并发模式说明

- **关闭（默认）**：图片逐张生成，适合有速率限制的 API
- **开启**：图片并行生成（最多15张同时），速度更快

---

## 注意事项

1. **API 配额限制**: 注意 Gemini 和图片生成 API 的调用配额
2. **生成时间**: 图片生成需要时间，请耐心等待

---

## 开源协议

本项目采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 协议

**你可以自由地：**
- 个人使用 - 用于学习、研究、个人项目
- 分享 - 在任何媒介以任何形式复制、发行本作品
- 修改 - 修改、转换或以本作品为基础进行创作

**但需要遵守以下条款：**
- 署名 - 必须给出适当的署名
- 非商业性使用 - 不得将本作品用于商业目的
- 相同方式共享 - 如果修改，必须以相同的协议分发

---

## 致谢

- [Google Gemini](https://ai.google.dev/) - 强大的 AI 能力
- 图片生成服务提供商

---

**渲染AI** - 让 AI 帮我们做更有创造力的事
