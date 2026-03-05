<div align="center">

<img src="frontend/public/logo.png" alt="MotifLab" width="200"/>

# MotifLab

**让传播不再需要门槛，让创作从未如此简单**

输入你的创意主题，让 AI 帮你生成爆款标题、正文和封面图。

*本项目基于 [HisMax/RedInk](https://github.com/HisMax/RedInk) 及其衍生项目改进而来，在此衷心感谢原作者的卓越贡献！*

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

- 并发生成所有页面
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

无论您是普通用户还是开发者，都可以从下面选择最适合您的部署方式。

### 方式一：Docker 一键部署（🔥推荐）

如果您只需要使用，不需要修改源码，这是最快且对环境毫无侵入的方式。

1. **前置要求**: 已安装 Docker 和 Docker Compose。
2. **启动命令**: 在包含 `docker-compose.yml` 的项目根目录下直接运行：

```bash
docker-compose up -d
```

启动后自动打开浏览器访问 <http://localhost:5173>

---

### 方式二：本地源码部署（适用开发者）

如果您想要做二次开发，或者您的机器无法运行 Docker，可采取传统的本地直接编译运行。

**前置要求**:

- Python 3.9+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+
- pnpm 9+

#### 1. 克隆项目与配置

首先获取源码并进入目录：

```bash
git clone https://github.com/urzeye/MotifLab.git
cd MotifLab
```

*提示：您可以将 `*.example` 复制一份并去掉 `.example` 后缀作为您的本地开发配置*。

#### 2. 分别安装与启动

为了方便联调，您可以分别开启两个终端运行前后端：

**终端 A：启动后端框架**

```bash
# 安装后端依赖（首次运行或依赖变更后执行）
uv sync
# 启动后端服务
uv run python backend/app.py
```

*(后端默认监听 `http://localhost:12398`)*

**终端 B：启动前端 Web**

```bash
cd frontend
# 安装前端所有的构建模块
pnpm install
# 本地热更新启动
pnpm dev
```

*(前端默认监听 `http://localhost:5173`)*

> ✅ **一键启动脚本（可选）**
> 如果您不想手动开两个终端，可使用仓库内脚本：
> - Windows: `scripts/start-windows.bat`
> - macOS / Linux / Git Bash: `bash scripts/start-all.sh`

*注：您可以在 Web 界面的**设置页面**直接配置您的外部模型 API 提供商及搜索功能。*

---

## 注意事项

1. **API 配额限制**: 注意大语言模型和图片生成 API 的调用配额方案。
2. **生成时间**: 由于批量并发和网络，图片生成需要一定时间，请耐心等待。
3. **敏感信息**: 切勿将带有明文 Key 的测试配置文件提交至版本控制。

---

## 开源协议

本项目基于原项目协议采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 协议开源。

**你可以自由地：**

- 个人使用 - 用于学习、研究、个人项目
- 分享 - 在任何媒介以任何形式复制、发行本作品
- 修改 - 修改、转换或以本作品为基础进行创作

**但需要遵守以下条款：**

- 署名 - 必须给出适当的署名（请提供指向原始协议及本项目 GitHub 链接的引用）
- 非商业性使用 - 不得将本作品用于商业目的
- 相同方式共享 - 如果修改，必须以相同的协议分发

---

## 致谢

- [HisMax/RedInk](https://github.com/HisMax/RedInk) - 本项目衍生的原仓库。感谢原作者出色的底层设计与开源奉献。

---

**MotifLab** - 让 AI 帮我们做更有创造力的事
