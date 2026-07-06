# 今天吃什么 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 `docs/prompts/what-to-eat.md` 实现一个可本地运行的“今天吃什么” FastAPI + React 个人选餐应用。

**Architecture:** 后端使用 FastAPI 提供食物库 CRUD、SSE 推荐、历史记录、统计和天气 API；SQLite 通过 `aiosqlite` 初始化和迁移。前端使用 React/Vite 以 hash tab 组织 4 个页面，通过 axios/fetch 调用 API，Recharts 渲染统计图，最终构建结果嵌入后端静态目录。

**Tech Stack:** Python, FastAPI, uvicorn, aiosqlite, pyyaml, openai SDK, httpx, pytest, React 19, Vite 8, axios, react-markdown, recharts。

---

## File Structure

- `config.yaml`：LLM、DB、天气、服务配置，API key 使用环境变量友好的占位值。
- `requirements.txt`、`pytest.ini`、`Makefile`：依赖、测试配置、常用命令；命令通过 `conda run -n other ...` 运行。
- `backend/config.py`：读取 YAML 并支持 `${ENV_VAR}` 环境变量覆盖。
- `backend/database.py`：SQLite 建表、幂等迁移、连接上下文、时段计算。
- `backend/models.py`：Pydantic v2 请求/响应模型。
- `backend/services/weather.py`：wttr.in + Nominatim 天气与地名服务，失败降级。
- `backend/services/llm.py`：构造中文 prompt、解析推荐结果、OpenAI 兼容流式调用。
- `backend/routers/*.py`：food、selection、history、stats、weather API。
- `backend/main.py`：FastAPI app、startup 初始化 DB、路由注册、静态文件/SPA fallback。
- `frontend/*`：Vite/React 应用、API 封装、四个页面和样式。
- `tests/test_core.py`：少量核心单元测试，覆盖时段、解析、价格统计桶等纯逻辑。

---

### Task 1: Project Skeleton and Configuration

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `Makefile`
- Create: `config.yaml`
- Create: `backend/__init__.py`
- Create: `backend/routers/__init__.py`
- Create: `backend/services/__init__.py`
- Create: `data/.gitkeep`

- [ ] **Step 1: Create dependency and command files**

Write Python dependencies exactly as specified in the prompt, plus `pydantic>=2` for explicit v2 support. Makefile commands should run through conda env `other`:

```makefile
.PHONY: help run build install setup test

help:
	@echo "今天吃什么 — 可用命令："
	@echo "  make install  安装依赖"
	@echo "  make build    构建前端并复制到后端静态目录"
	@echo "  make run      启动后端服务"
	@echo "  make test     运行后端测试"

run:
	conda run -n other uvicorn backend.main:app --reload

build:
	cd frontend && npm install && npm run build
	rm -rf backend/static && cp -r frontend/dist backend/static

install:
	conda run -n other pip install -r requirements.txt
	cd frontend && npm install

setup: install build
	@echo "✅ 完成！运行 'make run' 启动服务。"

test:
	conda run -n other pytest -q
```

- [ ] **Step 2: Create default config**

Use the prompt's defaults and keep API key as `${MODELSCOPE_API_KEY}` so no real secret is committed.

- [ ] **Step 3: Create package marker files and `data/.gitkeep`**

Create empty package marker files so imports work consistently.

---

### Task 2: Backend Core Modules

**Files:**
- Create: `backend/config.py`
- Create: `backend/models.py`
- Create: `backend/database.py`

- [ ] **Step 1: Implement config loader**

Read `config.yaml`, recursively convert dicts to `SimpleNamespace`, and expand environment variables in string values.

- [ ] **Step 2: Implement Pydantic models**

Define the models and literal service types from the prompt, using Pydantic v2-compatible `BaseModel` and `Field`.

- [ ] **Step 3: Implement database initialization**

Create both tables if missing, run idempotent `ALTER TABLE` statements, rebuild tables if `update_time` lacks `NOT NULL DEFAULT CURRENT_TIMESTAMP`, expose `get_db()` and `get_time_slot()`.

---

### Task 3: Backend Services

**Files:**
- Create: `backend/services/weather.py`
- Create: `backend/services/llm.py`

- [ ] **Step 1: Implement weather service**

Support optional lat/lon, concurrent wttr.in + Nominatim when coordinates exist, Chinese language settings, and fallback `WeatherResponse` data when requests fail.

- [ ] **Step 2: Implement LLM prompt and streaming**

Create a module-level `AsyncOpenAI` client, build the Chinese prompt from weather/history/options/preference, parse the final `推荐：A、B` line with the specified regex, and yield streaming chunks.

---

### Task 4: Backend Routers and App

**Files:**
- Create: `backend/routers/food.py`
- Create: `backend/routers/weather.py`
- Create: `backend/routers/stats.py`
- Create: `backend/routers/selection.py`
- Create: `backend/main.py`

- [ ] **Step 1: Implement `/api/food` CRUD**

List with pagination and soft-delete filtering; create with duplicate-name 409; update partial fields; delete by setting `deleted=1`.

- [ ] **Step 2: Implement `/api/weather`**

Call `get_weather(lat, lon)` and return `WeatherResponse`.

- [ ] **Step 3: Implement `/api/stats`**

Provide choice counts and price stats with weighted floor average and five fixed buckets.

- [ ] **Step 4: Implement `/api/select` and history endpoints**

POST SSE stream recommendations; persist `INSERT OR REPLACE`; provide history pagination, final-choice patch, and soft delete.

- [ ] **Step 5: Implement FastAPI app**

Initialize DB on startup, include all routers, mount built frontend when `backend/static` exists, and return JSON hint when frontend is not built.

---

### Task 5: Frontend App Shell and API

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/public/favicon.svg`
- Create: `frontend/public/icons.svg`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/api.js`

- [ ] **Step 1: Create Vite React package**

Use React 19, Vite 8, axios, react-markdown, recharts, and `@vitejs/plugin-react`.

- [ ] **Step 2: Implement API client**

Axios helpers for CRUD/history/stats/weather and native fetch SSE parser for POST `/api/select` with cancellation.

- [ ] **Step 3: Implement app shell**

Hash tabs for today/foods/history/stats, weather pill, geolocation timeout fallback, lazy load non-first-screen pages.

---

### Task 6: Frontend Pages and Styles

**Files:**
- Create: `frontend/src/pages/TodayPage.jsx`
- Create: `frontend/src/pages/FoodManager.jsx`
- Create: `frontend/src/pages/HistoryPage.jsx`
- Create: `frontend/src/pages/StatsPage.jsx`
- Create: `frontend/src/App.css`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Implement Today page**

Preference input, orange CTA, thinking animation, streamed markdown, two recommendation cards, and choice confirmation.

- [ ] **Step 2: Implement Food Manager page**

Inline add/edit/delete table, service type select, price input, pagination, backend detail error display, empty-page page correction.

- [ ] **Step 3: Implement History page**

Timeline layout, markdown reasoning collapses, optimistic final choice, optimistic single delete, serial batch delete, page-change cleanup.

- [ ] **Step 4: Implement Stats page**

Recharts pie chart, average price card, bucket bar chart, and ranking table with the specified palette and labels.

- [ ] **Step 5: Implement global styling**

Orange primary theme, green confirmation states, red errors, blue service tags, responsive cards/tables, `bounce`, `blink`, `fadeIn`, and `slideUp` animations.

---

### Task 7: Light Tests and Final Review

**Files:**
- Create: `tests/test_core.py`

- [ ] **Step 1: Add focused tests**

Test `parse_recommendation`, `get_time_slot`, and stats bucket helper behavior to catch core regressions without over-testing UI.

- [ ] **Step 2: Run backend tests**

Run: `conda run -n other pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Build frontend**

Run: `cd frontend && npm install && npm run build`

Expected: Vite build succeeds.

- [ ] **Step 4: Final review**

Run one unified final review of code and requirements coverage, then fix any concrete issues found.

---

## Self-Review Notes

- Spec coverage: plan maps every prompt section to backend, frontend, styles, tests, and final review tasks.
- Placeholder scan: no TBD/TODO placeholders are required for implementation; config API key remains an intentional environment-variable placeholder.
- Type consistency: backend model names, endpoint paths, and frontend API helper names align with the prompt.
