# ShadeCanopy-01 · 分区气候日志与轮灌计划

温室「分区气候日志与轮灌计划」全栈种子项目（非考勤 OA、非库存）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python Django 5 · Django REST Framework · SimpleJWT · django-cors-headers · Gunicorn |
| 前端 | Vue 3 · Vite · Pinia · Vue Router |
| 数据库 | PostgreSQL 15 |
| 部署 | Docker Compose · Nginx（前端容器反代 `/api` → Django） |

## 路径与端口

- **项目路径**：`D:\work\document\bytecode\claudeCodePro\ShadeCanopy\ShadeCanopy-01\`
- **前端**：http://localhost:3500
- **后端 API**：http://localhost:8500（也可经前端同源 `/api` 访问）
- **PostgreSQL**：localhost:5435

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | admin（管理员，可进 Django Admin） |
| `grower` | `123456` | grower（种植员） |

启动时 `entrypoint.sh` 会执行 `migrate` + `seed_data` 自动写入账号与示例业务数据。

## 快速启动

```bash
cd D:\work\document\bytecode\claudeCodePro\ShadeCanopy\ShadeCanopy-01
docker compose up --build
```

浏览器打开 http://localhost:3500 ，使用 `grower` / `123456` 登录。

停止：

```bash
docker compose down
```

## 业务模块

1. **Auth**：JWT `POST /api/auth/token/`，当前用户 `GET /api/auth/me/`
2. **Greenhouse**：name / location / areaM2 / notes
3. **Zone**：greenhouseId / zoneCode / cropName / status(`idle|growing|fallow`)；同温室 zoneCode 唯一
4. **ClimateLog**：zoneId / recordedAt / tempC / humidityPct / parUmol / co2Ppm；**humidityPct ∈ [20, 100]**；支持作废（见下）
5. **IrrigationCycle**：zoneId / startAt / durationMin / waterLiters / status(`scheduled|running|done|skipped`)
6. **Dashboard**：温室数、growing 分区数、近 24h 气候日志数、今日 scheduled 轮灌数 → `GET /api/dashboard/`

### 气候记录作废

异常气候记录采用**软作废**而非物理删除：作废行仍保留在库中，被其它逻辑引用时不做级联删除，任何接口都不得以物理删除冒充作废。

- ClimateLog 额外字段：`voidedAt`（作废时刻，可空）、`voidReason`（作废原因，可空）、`isVoided`（布尔标记）。
- `POST /api/climate-logs/{id}/void/`：请求体 `{"reason": "..."}`，`reason` 可省略或为空串；**去空白后非空时至少 6 个字**，否则 400。接口写入 `voidedAt`（服务端当前时刻）与去空白后的 `voidReason`。对已作废记录再次作废返回 **409 Conflict**。
- 默认列表 `GET /api/climate-logs/` **不含作废行**；带 `includeVoided=true` 时返回全部行，作废行通过 `isVoided` / `voidedAt` / `voidReason` 打标。`zoneId` 过滤在两种模式下均生效。
- 看板 `climateLogLast24h`（近 24h 气候计数）**排除作废行**。
- `GET /api/climate-logs/stats/void/` 返回 `{"voidedTotal": 已作废总数, "validTotal": 有效总数}`（可带 `zoneId`）。统计口径：`validTotal` 与默认列表（不含作废）的总数一致；`voidedTotal` 与 `includeVoided=true` 列表中作废行数量一致。

## API 一览

| 方法 | 路径 |
| --- | --- |
| POST | `/api/auth/token/` |
| POST | `/api/auth/token/refresh/` |
| GET | `/api/auth/me/` |
| CRUD | `/api/greenhouses/` |
| CRUD | `/api/zones/?greenhouseId=&status=` |
| CRUD | `/api/climate-logs/?zoneId=&includeVoided=true` |
| POST | `/api/climate-logs/{id}/void/` |
| GET | `/api/climate-logs/stats/void/?zoneId=` |
| CRUD | `/api/irrigation-cycles/?zoneId=&status=` |
| GET | `/api/dashboard/` |

字段对外使用 camelCase（如 `areaM2`、`zoneCode`、`humidityPct`）。

## 本地开发（可选）

**后端**（需本机 Postgres 或已启动 compose 中的 db）：

```bash
cd backend
pip install -r requirements.txt
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5435
python manage.py migrate
python manage.py seed_data
python manage.py runserver 0.0.0.0:8500
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

Vite 已将 `/api` 代理到 `http://127.0.0.1:8500`。

## 目录结构

```
ShadeCanopy-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh      # migrate + seed + gunicorn
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/            # settings / urls
│   ├── accounts/          # 自定义 User + role
│   └── core/              # 温室/分区/气候/轮灌 + seed_data
└── frontend/
    ├── Dockerfile
    ├── nginx.conf         # 静态资源 + /api 反代
    ├── package.json
    └── src/               # Vue 页面（叶绿/土色主题）
```

## 配色说明

前端采用叶绿（`#3d6b3a`）与土色（`#8b6b45`）主色，米色底与侧栏深绿渐变，贴近温室场景。
