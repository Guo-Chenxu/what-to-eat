# 今天吃什么 — 完整项目 Prompt

> 将此 prompt 交给 AI，可从零完整复现本项目。

---

## 项目概述

构建一个名为 **"今天吃什么"** 的个人选餐 Web 应用。用户维护一个美食库，点击按钮后 AI 根据当前天气、时段、近期饮食历史和当天偏好，流式输出推荐理由并给出 2 个候选食物；用户点击确认最终吃了哪个，历史和统计页面随之更新。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python · FastAPI · uvicorn · aiosqlite (SQLite) · openai SDK · httpx · pyyaml |
| 前端 | React 19 · Vite 8 · axios · react-markdown · recharts |
| LLM | 任意 OpenAI 兼容 API（默认 ModelScope DeepSeek-V4-Flash） |
| 天气 | wttr.in（免费，无需 key）+ Nominatim 反向地理编码 |

---

## 目录结构

```
what-to-eat/
├── config.yaml                 # LLM / DB / 天气 / 服务配置
├── requirements.txt
├── Makefile
├── pytest.ini
├── backend/
│   ├── __init__.py
│   ├── config.py               # 读取 config.yaml → SimpleNamespace
│   ├── database.py             # aiosqlite 初始化、迁移、get_db、get_time_slot
│   ├── main.py                 # FastAPI app、静态文件挂载、SPA fallback
│   ├── models.py               # Pydantic v2 models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── food.py             # /api/food CRUD
│   │   ├── selection.py        # /api/select (SSE) + /api/history
│   │   ├── stats.py            # /api/stats/choices + /api/stats/price
│   │   └── weather.py          # /api/weather
│   └── services/
│       ├── __init__.py
│       ├── llm.py              # build_prompt、parse_recommendation、stream_food_recommendation
│       └── weather.py          # get_weather (wttr.in + Nominatim)
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── main.jsx
│       ├── App.jsx             # tab 路由（hash）、天气拉取、布局
│       ├── App.css             # 全局 + 各页面样式
│       ├── index.css           # reset + 动画 + 组件细节样式
│       ├── api.js              # axios 封装 + startSelection (SSE fetch)
│       └── pages/
│           ├── TodayPage.jsx   # 今天吃什么主页
│           ├── FoodManager.jsx # 美食库增删改查
│           ├── HistoryPage.jsx # 历史记录 + 删除
│           └── StatsPage.jsx   # 饼图 + 柱状图 + 排行榜
└── data/
    └── what_to_eat.db          # SQLite 数据文件（运行时自动创建）
```

---

## 配置文件

### `config.yaml`

```yaml
llm:
  base_url: "https://api-inference.modelscope.cn/v1"
  api_key: "<YOUR_API_KEY>"   # ⚠️ 请勿将真实 key 提交至版本库，建议用环境变量或 git-ignored 文件注入
  model: "deepseek-ai/DeepSeek-V4-Flash"

database:
  path: "data/what_to_eat.db"

weather:
  city: "Beijing"       # 无法获取定位时的降级城市
  language: "zh-cn"    # 传入 wttr.in URL 的 lang 参数，可配置

app:
  host: "0.0.0.0"
  port: 8000
```

### `requirements.txt`

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
aiosqlite>=0.20.0
pyyaml>=6.0
openai>=1.30.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

### `Makefile`

```makefile
.PHONY: help run build install setup

help: ## 显示帮助信息
	@echo "今天吃什么 — 可用命令："
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

run: ## 启动后端服务
	@uvicorn backend.main:app --reload

build: ## 构建前端并嵌入后端静态目录
	cd frontend && npm install && npm run build
	rm -rf backend/static && cp -r frontend/dist backend/static

install: ## 安装所有依赖（Python + Node）
	pip install -r requirements.txt
	cd frontend && npm install

setup: install build ## 一键安装 + 构建（首次使用）
	@echo "✅ 完成！运行 'make run' 启动服务。"
```

---

## 后端实现

### `backend/config.py`

读取 `config.yaml`，递归转换为 `SimpleNamespace` 供点访问：

```python
from pathlib import Path
from types import SimpleNamespace
import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

def _dict_to_namespace(d):
    ns = SimpleNamespace()
    for key, value in d.items():
        setattr(ns, key, _dict_to_namespace(value) if isinstance(value, dict) else value)
    return ns

settings = _dict_to_namespace(yaml.safe_load(open(_CONFIG_PATH, encoding="utf-8")))
```

### `backend/models.py`

Pydantic v2 models：

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

SLOT_NAMES = {1: "午餐", 2: "晚餐", 3: "夜宵"}
ServiceType = Literal["外卖", "到店<100m", "到店<500m", "到店<1km", "到店<2km"]

class FoodOptionCreate(BaseModel):
    name: str
    type: str
    characteristics: str
    service_type: ServiceType
    avg_price: int = Field(gt=0)

class FoodOptionUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    characteristics: str | None = None
    service_type: ServiceType | None = None
    avg_price: int | None = Field(default=None, gt=0)

class FoodOptionResponse(BaseModel):
    id: int; name: str; type: str; characteristics: str
    service_type: str; avg_price: int; create_time: str; update_time: str

class SelectionResponse(BaseModel):
    id: int; date: str; time_slot: int; slot_name: str
    food_1: str; food_2: str; reasoning: str | None; weather: str | None
    location: str | None; final_choice: str | None; today_preference: str | None
    create_time: str

class SelectRequest(BaseModel):
    today_preference: str | None = None

class ChoiceUpdate(BaseModel):
    final_choice: str

class HistoryPageResponse(BaseModel):
    items: list[SelectionResponse]; total: int; page: int; page_size: int; total_pages: int

class FoodPageResponse(BaseModel):
    items: list[FoodOptionResponse]; total: int; page: int; page_size: int; total_pages: int

class ChoiceStatItem(BaseModel):
    name: str; count: int

class PriceDistItem(BaseModel):
    range: str; count: int

class PriceStatsResponse(BaseModel):
    avg_price: int; distribution: list[PriceDistItem]

class WeatherResponse(BaseModel):
    temp: str; description: str; city: str; location: str
```

### `backend/database.py`

SQLite 初始化 + 增量迁移 + 重建策略：

**两张表：**

**`food_options`**：`id, name(UNIQUE), type, characteristics, service_type(默认'到店<500m'), avg_price(默认30), create_time, update_time, deleted(软删除)`

**`selections`**：`id, date, time_slot, food_1, food_2, reasoning, weather, location, final_choice, today_preference, create_time, update_time, deleted, UNIQUE(date, time_slot)`

**迁移策略**：
1. `CREATE TABLE IF NOT EXISTS` 建表
2. 逐条执行 `ALTER TABLE` 列表（用 try/except 忽略已存在）
3. 检查 `update_time` 是否同时具备 `NOT NULL` 且 `DEFAULT CURRENT_TIMESTAMP`（字面量），两者缺一均触发重建（`CREATE TABLE _new → INSERT SELECT → DROP → RENAME`）

**时段划分** (`get_time_slot`):
- 时段1（午餐）: 0:00–13:59
- 时段2（晚餐）: 14:00–18:59
- 时段3（夜宵）: 19:00+

**`get_db()`**: `asynccontextmanager`，设置 `db.row_factory = aiosqlite.Row`

### `backend/services/weather.py`

- 调用 `https://zh.wttr.in/{query}?format=j1&lang={language}`（`language` 来自 `settings.weather.language`，可配置）
- 若有 lat/lon，同时调用 Nominatim 反向地理编码（`https://nominatim.openstreetmap.org/reverse`，**查询参数** `accept-language=zh-CN`，HTTP 头仅含 `User-Agent`）获取中文地名（city > town > county > suburb）
- 有 lat/lon 时用 `asyncio.gather` 并发请求天气 + Nominatim；无坐标时仅单个顺序请求天气，location 降级为配置城市名
- 任何异常均降级返回"无法获取天气"

### `backend/services/llm.py`

**`build_prompt(weather, history, food_options, current_date, slot_name, today_preference)`**:

构建 prompt 模板（中文）：
- 角色：美食推荐助手
- 输入：天气、日期时段、近7天历史（只含有 final_choice 的记录）、今日偏好（optional，备注"可参考，不必强求，综合考虑即可"）、食物列表（name、type、characteristics、service_type、avg_price）
- 要求：分析推荐理由，**最后一行严格**按格式输出：`推荐：{食物名称1}、{食物名称2}`

**`parse_recommendation(full_text)`**:
- 正则 `r"推荐[：:]\s*(.+?)\s*[、,，]\s*(.+?)\s*$"`，传入 `re.MULTILINE` 标志（`$` 锚定每行行尾），取最后一个匹配
- 失败返回 `("?", "?")`

**`stream_food_recommendation(...)`**:
- 模块级单例 `client = AsyncOpenAI(base_url, api_key)`（模块导入时初始化一次，函数复用该实例，不在每次调用时重新创建）
- `client.chat.completions.create(..., stream=True)` 流式调用
- yield 每个 chunk 的 `content`（跳过空 choices）

### `backend/routers/food.py`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/food` | 分页列表，默认 page=1（最小1，负值/0自动修正）page_size=15（范围1–100，超界自动夹紧），软删过滤，id DESC |
| POST | `/api/food` | 创建，name UNIQUE 冲突返回 409，成功返回 201 |
| PUT | `/api/food/{food_id}` | 局部更新，未提供字段保留原值，更新 update_time，记录不存在返回 404 |
| DELETE | `/api/food/{food_id}` | 软删除（deleted=1），同时更新 update_time，记录不存在返回 404，返回 `{"message": "删除成功"}` |

### `backend/routers/selection.py`

**`POST /api/select`**（Query: `lat`, `lon`；Body: `SelectRequest`（可选，未提供时 today_preference 视为 None））:
1. 解析 `today_preference`（先 strip，空字符串或纯空白均视为 None）
2. 根据当前时间获取 `time_slot`、`slot_name`
3. `get_weather(lat, lon)` → `weather_str, location_str`
4. 查近7天历史（排除当天同时段，软删过滤），拼为 history list
5. 查全部食物选项（含 service_type、avg_price）
6. `StreamingResponse` 返回 SSE：
   - 流式 yield `data: {"content": chunk}` 每个文本块
   - 流结束后 `parse_recommendation` 解析 food_1, food_2
   - `INSERT OR REPLACE INTO selections`（UNIQUE date+time_slot，重复时覆盖）
   - yield `data: {"type": "done", "id": record_id, "food_1": ..., "food_2": ...}`

**`GET /api/history`**（page, page_size≤50）: 分页，软删过滤，create_time DESC，行添加 slot_name

**`PATCH /api/history/{id}/choice`**（Body: `ChoiceUpdate`）: 记录 final_choice

**`DELETE /api/history/{id}`**: 软删除

### `backend/routers/stats.py`

**`GET /api/stats/choices`**: `GROUP BY final_choice COUNT(*) ORDER BY count DESC`，过滤 `deleted=0` 且 `final_choice IS NOT NULL AND final_choice != ''`

**`GET /api/stats/price`**: JOIN food_options 按 avg_price 聚合，同时过滤 `s.deleted=0 AND fo.deleted=0` 及 `final_choice IS NOT NULL AND final_choice != ''`；计算**地板整除加权均价**（`total_weighted // total_count`，向零截断，非四舍五入）和5个价格桶分布：
- `<25`（0–24）、`25-34`、`35-44`、`45-54`、`≥55`（55+，Unicode ≥ 符号）

### `backend/main.py`

```python
app = FastAPI(title="今天吃什么", version="1.0.0")
# startup: init_db()
# include_router: food, weather, selection, stats
# 若 backend/static 存在且非空：
#   挂载 /assets → StaticFiles(assets_dir)
#   GET /{full_path:path} → FileResponse(index.html)  ← SPA fallback
# 否则返回 JSON 提示前端未构建
```

---

## 前端实现

### `frontend/vite.config.js`

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } } },
  build: { outDir: 'dist' }
})
```

### `frontend/src/api.js`

- `axios.create({ baseURL: '/' })` 基础实例
- `getWeather(coords)` → `GET /api/weather?lat=&lon=`
- `getFoods(page, pageSize)` → `GET /api/food`
- `createFood / updateFood / deleteFood` → POST/PUT/DELETE `/api/food`
- `getHistory(page, pageSize)` → `GET /api/history`
- `setFinalChoice(id, finalChoice)` → `PATCH /api/history/{id}/choice`
- `deleteHistory(id)` → `DELETE /api/history/{id}`
- `getChoiceStats / getPriceStats` → GET stats 接口
- **`startSelection(onChunk, onDone, onError, coords, preference)`**:
  - 用原生 `fetch` + `ReadableStream` 解析 SSE（不用 EventSource，支持 POST）
  - Body 含 `today_preference`（仅非空时发送）
  - 解析 `data: {...}` 行，`type==='done'` 调 `onDone`，否则若 `data.content` 存在则调 `onChunk(data.content)`（无 content 字段的事件静默丢弃）
  - 返回 cancel 函数（`AbortController.abort()`）

### `frontend/src/App.jsx`

- 4个 Tab：`today / foods / history / stats`，用 URL hash 持久化（`window.location.hash`，监听 `popstate`）
- `FoodManager / HistoryPage / StatsPage` 懒加载（`React.lazy + Suspense`），`TodayPage` 即时加载
- App 级拉取天气（`navigator.geolocation.getCurrentPosition`，超时5s降级）
- Header 显示：`📍 {location} · {description} · {temp}`（天气 pill 样式）
- 将 `coords` 传给 `TodayPage`

### `frontend/src/pages/TodayPage.jsx`

状态：`status(idle|loading|done|error) / streamText / recommendations({id,food_1,food_2}) / chosenFood / preference`；`cancelRef`（`useRef`）存储 `startSelection` 返回的取消函数，空依赖 `useEffect` 在组件卸载时调用以终止进行中的 SSE 流

UI 流程：
1. **今日偏好输入框**（placeholder "今日偏好（选填）：想吃清淡的？辣的？不想动脑点外卖？"，maxLength=100，loading 时 disabled）
2. **大橙色圆角按钮** "🎲 今天吃什么？" / loading 时 "🤔 思考中..."
3. loading 且无文字 → **thinking-box**（含 `AI 正在思考` 标签 + 跳动三圆点动画，`bounce` keyframe）
4. 有流式文字 → **stream-box**（含 `✦ AI 分析中/AI 分析` 标签、`ReactMarkdown` 渲染、loading 时闪烁光标；status=loading 时同时携带 `streaming` CSS 类）
5. done → 动态 `<h2>`（未选时显示"今天推荐吃"，确认后显示"✅ 今天吃这个"）+ **推荐卡片**（两张，橙色边框；food_1 图标 🥢，food_2 图标 🍴，已选卡片图标改为 ✅；点"选这个"确认；已选卡片高亮绿色并显示"已确认"标签，另一张变暗淡；未确认前卡片下方显示提示段落"点击确认你最终的选择，下次推荐将参考此记录"）
6. error → 红色错误提示

### `frontend/src/pages/FoodManager.jsx`

- 表格列：名称、类型、特点、获取方式、人均、操作
- 获取方式用 `<select>`（5个选项），人均用 `<input type="number" min=1>`（带 ¥ 前缀）
- 行内编辑（点编辑展开输入框）+ 顶部新增行（点"+ 添加食物"显示）
- 分页：15条/页，`page_size` 上限100
- 删除后自动处理页码（若当前页变空则跳至末页）
- 错误显示（前端透传后端 `detail` 字段；name 重复时后端返回"食物名称已存在"；添加失败兜底"添加失败"，保存失败兜底"保存失败"）

### `frontend/src/pages/HistoryPage.jsx`

- 时间线布局（左侧竖线 + 橙色圆点）
- 每条记录显示：日期、时段（☀️ 午餐/🌅 晚餐/🌙 夜宵）、📍位置、🌤天气
- **两个食物 chip**：未选时有小 ✓ 按钮可确认；已选 chip 前缀 ✅ 并高亮绿色，另一个变淡（确认选择同样使用**乐观更新**：先写入 `localChoices`，API 失败时回滚）
- **"▼ 查看AI分析"** 折叠展开（ReactMarkdown 渲染）
- **删除功能**：
  - 每条右上角常驻 🗑 按钮（hover 变红），单条确认删除；**批量删除进行中（`deleting` 状态）时置为 disabled**
  - "选择"按钮进入批量模式：复选框 + "删除选中（N）"按钮（全角括号）
  - **单条删除**用乐观更新（先从本地移除，API 失败时回滚恢复原记录）
  - **批量删除**串行执行（避免并发写冲突）；批量路径无回滚——先整体从本地移除，失败时仅 alert 提示失败条数，需手动刷新页面重新看到未删成功的记录
- 翻页时自动折叠已展开的 AI 分析、清空本地已确认选择、平滑滚动到列表顶部
- 分页：10条/页

### `frontend/src/pages/StatsPage.jsx`

使用 **Recharts**：
- **饼图**（`PieChart + Pie`）：选择次数分布，混合16色调色板（前10个橙色调 + 2绿 + 1蓝 + 1紫 + 1粉 + 1灰），内嵌百分比标签（< 4% 不显示）
- **均价卡片**（`avg-price-card`）：橙色大字显示平均消费
- **柱状图**（`BarChart + Bar`）：5个价格桶分布，圆角柱
- **排行榜表格**：排名（🥇🥈🥉/数字）、食物名（带颜色圆点）、次数、进度条+百分比

---

## 样式设计

**主色调**：`#ff6b35`（橙色）  
**辅色**：`#22c55e`（确认绿）、`#e53e3e`（错误红）、`#3b82f6`（服务类型蓝）

**关键动画**：
- `bounce`：三圆点跳动（思考等待）
- `blink`：光标闪烁（流式输出时）
- `fadeIn`：stream-box 淡入
- `slideUp`：推荐卡片滑入（两张分别延迟0/0.15s）

**布局**：
- `.app` 最大宽1200px，水平居中，32px 内边距
- `.app-header` 上方 h1 + 右侧天气 pill，下方 tab 导航
- Tab 按钮：底部3px 橙色边框指示激活态
- 非首屏页面懒加载（Suspense fallback "加载中..."）

---

## 数据流

```
用户点击"今天吃什么"
  → POST /api/select (SSE)
    ← 天气（wttr.in + Nominatim）
    ← 近7天历史（SQLite）
    ← 全部食物（SQLite）
    → build_prompt → LLM stream
    ← SSE chunks（data: {content: "..."}）→ 前端实时渲染
    ← parse_recommendation → INSERT selections
    ← SSE done（data: {type:"done", id, food_1, food_2}）
用户点"选这个"
  → PATCH /api/history/{id}/choice
```

---

## 关键设计决策

1. **SSE 用 POST + fetch**（非 EventSource）：支持携带请求体（今日偏好）
2. **`INSERT OR REPLACE`**：同一天同一时段重复推荐时覆盖（`UNIQUE(date, time_slot)`）
3. **软删除**：`food_options` 和 `selections` 均有 `deleted` 字段，不物理删除
4. **DB 迁移**：幂等 ALTER TABLE 列表 + 条件重建（保证 `update_time NOT NULL DEFAULT CURRENT_TIMESTAMP`）
5. **天气定位降级**：有 GPS → 用坐标；拒绝授权/超时 → 用 config.yaml 中的城市名
6. **今日偏好**：LLM prompt 中标注"可参考，不必强求，综合考虑即可"，给 LLM 软约束
7. **History 乐观更新**：单条删除先从本地移除，请求失败再回滚；批量删除整体乐观移除但失败时不回滚（alert 提示失败条数，需手动刷新）；确认食物选择同样乐观更新（先写入 `localChoices`，API 失败时回滚）
8. **Code splitting**：TodayPage 直接 import（首屏），其余三页 `React.lazy`
9. **Tab hash 路由**：URL hash 持久化，监听 `popstate` 支持浏览器前进/后退
10. **时段划分**：按小时切分（<14: 午餐，14–18: 晚餐，19+: 夜宵），每天每时段唯一一条推荐记录

---

## 启动方式

```bash
# 首次
make setup      # 安装依赖 + 构建前端 + 嵌入后端
make run        # 启动 uvicorn，访问 http://localhost:8000

# 开发（前后端分离热更新）
uvicorn backend.main:app --reload   # 后端 :8000
cd frontend && npm run dev          # 前端 :5173，/api 代理到 :8000
```

