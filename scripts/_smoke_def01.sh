#!/usr/bin/env bash
# DEF-01 冒烟：保存家庭档案 -> 重启服务 -> 读回；验证 GET / 返回档案管理页
set -u
ROOT="/c/Users/93663/Desktop/Home_Flavor"
PORT=8877
BASE="http://127.0.0.1:${PORT}"
SMOKE_DIR="/tmp/ff_smoke"
SMOKE_WIN="C:/Users/93663/AppData/Local/Temp/ff_smoke"   # Windows 绝对路径（Python 可解析）
DB_URL="sqlite:///${SMOKE_WIN}/smoke.db"
mkdir -p "$SMOKE_DIR"
rm -f "$SMOKE_DIR/smoke.db"

fail() { echo "SMOKE_FAIL: $1"; exit 1; }

start_srv() {
  (cd "$ROOT" && PYTHONPATH=./.deps DB_URL="$DB_URL" python -m uvicorn app.main:app --port "$PORT" > "$SMOKE_DIR/srv.log" 2>&1) &
  SRV_PID=$!
  for i in $(seq 1 40); do
    curl -s -o /dev/null "$BASE/api/family" && return 0
    sleep 0.5
  done
  echo "--- server log ---"; tail -30 "$SMOKE_DIR/srv.log"
  fail "服务未就绪"
}
stop_srv() {
  kill "$SRV_PID" 2>/dev/null
  for pid in $(netstat -ano 2>/dev/null | grep ":$PORT" | grep LISTENING | awk '{print $NF}' | sort -u); do
    taskkill //F //PID "$pid" >/dev/null 2>&1
  done
  sleep 1
}

# ===== 第一段：启动并保存档案 =====
start_srv
echo "== 1) GET /api/family（自动建默认家庭）=="
FAM1=$(curl -s "$BASE/api/family")
echo "$FAM1" | grep -q '"id"' || fail "GET family 异常: $FAM1"
echo "OK -> $FAM1"

echo "== 2) PUT /api/family 改名 武汉小家 =="
printf '{"name":"武汉小家"}' > "$SMOKE_DIR/fam_body.json"
RES=$(curl -s -X PUT "$BASE/api/family" -H "Content-Type: application/json" --data-binary @"$SMOKE_DIR/fam_body.json")
echo "$RES" | grep -q '武汉小家' || fail "PUT family 失败: $RES"
echo "OK -> $RES"

echo "== 3) POST /api/members 新增 小明 =="
printf '{"name":"小明","age":6,"gender":"male","diet_goal":"normal","constitution":["balanced"],"health_conditions":["none"],"allergens":["peanut"],"dietary_restrictions":["不吃香菜"]}' > "$SMOKE_DIR/mem_body.json"
RES=$(curl -s -X POST "$BASE/api/members" -H "Content-Type: application/json" --data-binary @"$SMOKE_DIR/mem_body.json")
echo "$RES" | grep -q '"id"' || fail "POST member 失败: $RES"
MID=$(echo "$RES" | sed -n 's/.*"id":\([0-9]*\).*/\1/p')
echo "OK -> $RES (id=$MID)"

echo "== 4) GET / 应为档案管理页 =="
HTML=$(curl -s "$BASE/")
echo "$HTML" | grep -q '家庭 AI 食谱推荐系统' || fail "GET / 未返回档案页"
echo "OK -> 首页包含档案页标题"

stop_srv

# ===== 第二段：重启服务（同库）后读回 =====
echo "======== 模拟重启 ========"
start_srv
echo "== 5) 重启后 GET /api/family 应读回 武汉小家 =="
FAM2=$(curl -s "$BASE/api/family")
echo "$FAM2" | grep -q '武汉小家' || fail "重启后家庭名丢失: $FAM2"
echo "OK -> $FAM2"

echo "== 6) 重启后 GET /api/members 应读回 小明 =="
MEM2=$(curl -s "$BASE/api/members")
echo "$MEM2" | grep -q '小明' || fail "重启后成员丢失: $MEM2"
echo "OK -> $MEM2"

stop_srv
echo "SMOKE_ALL_PASS"