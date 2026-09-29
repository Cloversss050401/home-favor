<template>
  <div class="page-wrap">
    <!-- 页面标题 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">做菜反馈</h2>
        <p class="page-sub">
          勾选今天实际制作的菜品，填写各成员食用分量；一键全选可复用 AI 推荐分配，手动输入优先级更高。
        </p>
      </div>
    </div>

    <!-- 步骤指示 -->
    <el-steps :active="currentStep" align-center finish-status="success" class="step-bar">
      <el-step title="选择方案" description="挑选本次反馈的食谱" />
      <el-step title="勾选菜品" description="标记实际制作的菜" />
      <el-step title="设置分量" description="填写每位成员食用量" />
      <el-step title="提交反馈" description="生成营养统计依据" />
    </el-steps>

    <!-- 步骤 1：选择方案 -->
    <div class="glass-card card-section">
      <div class="card-head">
        <span class="section-title"><el-icon><Document /></el-icon>第一步 · 选择食谱方案</span>
        <el-tag v-if="record" type="success" effect="plain" round>已选择</el-tag>
      </div>
      <div class="select-row">
        <el-select
          v-model="selectedRecordId"
          placeholder="选择历史生成的食谱方案（默认最近一次）"
          style="width: 480px; max-width: 100%"
          @change="onRecordChange"
        >
          <el-option
            v-for="r in records"
            :key="r.id"
            :label="`#${r.id} · ${fmt(r.created_at)} · ${mealLabel(r.meal_type)} · ${(r.shared_dishes || []).length} 道菜`"
            :value="r.id"
          />
        </el-select>
        <el-select v-model="mealType" style="width: 110px">
          <el-option v-for="o in MEAL_TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-date-picker
          v-model="eatenDate"
          type="date"
          placeholder="实际制作日期"
          value-format="YYYY-MM-DD"
        />
      </div>
      <div class="text-muted" style="font-size: 12px; margin-top: 6px">
        餐次默认取所选方案（未限定时默认晚餐）；实际吃了哪一餐，选哪一餐。
      </div>
    </div>

    <!-- 步骤 2 & 3：菜品勾选 + 分量 -->
    <div class="glass-card card-section" v-if="record">
      <div class="card-head">
        <span class="section-title"><el-icon><Dish /></el-icon>第二、三步 · 勾选菜品并设置分量</span>
        <el-button :icon="Select" type="primary" plain @click="applyAiAmount">
          一键全选（复用 AI 分配分量）
        </el-button>
      </div>

      <el-table :data="record.shared_dishes" border>
        <el-table-column width="60" align="center">
          <template #default="{ row }">
            <el-checkbox :model-value="isChecked(row.name)" @change="toggleDish(row.name)" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="菜品" min-width="140">
          <template #default="{ row }">
            <span class="dish-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="主料" min-width="160">
          <template #default="{ row }">{{ (row.main_ingredients || []).join('、') || '—' }}</template>
        </el-table-column>
        <el-table-column label="成员食用分量" min-width="430">
          <template #default="{ row }">
            <div v-if="isChecked(row.name)" class="member-grid">
              <div v-for="m in recordMembers()" :key="m.member_id" class="member-cell">
                <span class="mname">{{ m.member_name }}</span>
                <el-checkbox
                  v-model="row.aiFlags[m.member_id]"
                  :disabled="hasManual(row, m.member_id)"
                  size="small"
                >
                  AI 分配
                </el-checkbox>
                <el-input-number
                  v-model="row.portions[m.member_id]"
                  :min="0"
                  :max="1.5"
                  :step="0.1"
                  :precision="2"
                  size="small"
                  controls-position="right"
                  :disabled="row.aiFlags[m.member_id]"
                  placeholder="比例"
                />
                <span class="unit-hint">份</span>
              </div>
            </div>
            <span v-else class="text-muted">未勾选</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="submit-row">
        <el-button type="success" size="large" :icon="Check" :loading="saving" @click="submitFeedback">
          提交反馈
        </el-button>
        <span class="text-muted submit-hint">
          每道菜每位成员二选一：勾「AI 分配」= 复用推荐分量（算估算）；填「比例」= 手动输入实际吃了多少（0.5 表示吃半份）。
        </span>
      </div>

      <!-- 方案外的菜（用户实际做了推荐之外的自做菜） -->
      <div class="custom-dish-box">
        <div class="custom-title">做了方案外的菜？这里补记（营养按主料折算）</div>
        <div class="custom-form">
          <el-input v-model="customName" placeholder="菜名，如：红烧肉" style="width: 170px" maxlength="30" />
          <el-input v-model="customIngredients" placeholder="主料，逗号分隔：五花肉、土豆、青椒" style="width: 300px" maxlength="100" />
          <el-input-number v-model="customPortion" :min="0.1" :max="1.5" :step="0.1" :precision="2" controls-position="right" style="width: 110px" />
          <span class="text-muted" style="font-size: 12px">每人吃几份</span>
          <el-button :icon="Plus" type="primary" plain @click="addCustomDish">加入记录</el-button>
        </div>
        <div v-if="customList.length" class="custom-list">
          <el-tag
            v-for="(c, i) in customList"
            :key="i"
            closable
            size="small"
            effect="plain"
            @close="customList.splice(i, 1)"
          >
            {{ c.name }}（{{ c.ingredients.join('、') }}）× {{ c.portion }} 份
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 反馈历史（按日期分组的时间线） -->
    <div class="glass-card card-section">
      <div class="card-head">
        <span class="section-title"><el-icon><Clock /></el-icon>最近反馈记录</span>
        <el-tag type="info" effect="plain" round>{{ history.length }} 条</el-tag>
      </div>

      <!-- 概览卡 -->
      <div class="overview-row">
        <div class="ov-card">
          <div class="ov-num">{{ recordDays }}</div>
          <div class="ov-label">记录天数</div>
        </div>
        <div class="ov-card">
          <div class="ov-num">{{ recordMemberCount }}</div>
          <div class="ov-label">涉及成员</div>
        </div>
        <div class="ov-card">
          <div class="ov-num">{{ history.length }}</div>
          <div class="ov-label">记录条数</div>
        </div>
        <div class="ov-card ov-card--warn" v-if="latestDate">
          <div class="ov-num ov-num--warn">{{ latestDate }}</div>
          <div class="ov-label">最近记录日期</div>
        </div>
      </div>

      <!-- 时间线：按日期分组，卡内按成员分块 -->
      <div v-if="groupedHistory.length" class="timeline">
        <div v-for="grp in groupedHistory" :key="grp.date" class="tl-day">
          <div class="tl-date">{{ grp.date }} <span class="tl-day-tag">{{ grp.dayOfWeek }}</span></div>
          <div class="tl-body">
            <div v-for="m in grp.members" :key="m.member_id" class="tl-member">
              <div class="tl-member-name">{{ memberName(m.member_id) }}</div>
              <div class="tl-rows">
                <div v-for="(r, ri) in m.items" :key="ri" class="tl-row">
                  <span class="tl-dish">{{ r.dish_name }}</span>
                  <span class="tl-amount">{{ Number(r.amount_g) }}g</span>
                  <el-tooltip v-if="r.recAmount" :content="`AI 推荐 ${Number(r.recAmount)}g`" placement="top">
                    <span class="tl-cmp" :class="cmpClass(r)">{{ cmpText(r) }}</span>
                  </el-tooltip>
                  <span class="tl-src" :class="r.is_ai_recommended ? 'src-ai' : 'src-manual'">
                    {{ r.is_ai_recommended ? '⚡ 估算' : '✎ 实际' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-muted" style="padding: 12px 0">暂无反馈记录</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Clock, Dish, Document, Plus, Select } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import http, { MEAL_TYPE_OPTIONS } from '../api'

const records = ref([])
const selectedRecordId = ref(null)
const record = ref(null)
const eatenDate = ref(dayjs().format('YYYY-MM-DD'))
const mealType = ref('dinner')
const history = ref([])
const saving = ref(false)
const submitted = ref(false)
const membersCache = ref([])

// 方案外自定义菜
const customName = ref('')
const customIngredients = ref('')
const customPortion = ref(1)
const customList = ref([])

const fmt = (v) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '—')
const mealLabel = (v) => MEAL_TYPE_OPTIONS.find((o) => o.value === v)?.label || '不限餐次'

const currentStep = computed(() => {
  // 提交成功：四步全部打钩
  if (submitted.value) return 4
  if (!record.value) return 0
  const checkedDishes = record.value.shared_dishes.filter(
    (d) => record.value.checked[d.name]
  )
  if (!checkedDishes.length) return 1
  // 已勾选菜品但还没设置任何分量：停在第三步（设置分量）
  const members = recordMembers()
  const hasPortion = checkedDishes.some((d) =>
    members.some((m) => d.aiFlags[m.member_id] || hasManual(d, m.member_id))
  )
  // 分量已设置：第三步打钩，停在第四步（提交反馈）
  return hasPortion ? 3 : 2
})

function isChecked(name) {
  return !!record.value.checked[name]
}

function toggleDish(name) {
  record.value.checked[name] = !record.value.checked[name]
}

function recordMembers() {
  const alloc = record.value.member_allocation || []
  return alloc
    .filter((a) => a.dishes && a.dishes.length)
    .map((a) => ({ member_id: a.member_id, member_name: a.member_name }))
}

function hasManual(row, memberId) {
  const v = row.portions[memberId]
  return v != null && Number(v) > 0
}

async function loadRecords() {
  try {
    const { data } = await http.get('/recipes/records')
    records.value = data.items || []
    if (records.value.length && !selectedRecordId.value) {
      selectedRecordId.value = records.value[0].id
      onRecordChange(selectedRecordId.value)
    }
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadMembers() {
  try {
    const { data } = await http.get('/members')
    membersCache.value = data.items || []
  } catch (e) {
    /* 忽略 */
  }
}

function onRecordChange(id) {
  const rec = records.value.find((r) => r.id === id)
  if (!rec) return
  submitted.value = false
  mealType.value = rec.meal_type || 'dinner'
  record.value = {
    ...rec,
    checked: {},
    shared_dishes: (rec.shared_dishes || []).map((d) => ({
      ...d,
      aiFlags: {},
      portions: {},
    })),
  }
}

function addCustomDish() {
  const name = customName.value.trim()
  const ings = customIngredients.value
    .split(/[,，]/)
    .map((x) => x.trim())
    .filter(Boolean)
  if (!name) return ElMessage.warning('请填写菜名')
  if (!ings.length) return ElMessage.warning('请填写至少一个主料')
  customList.value.push({ name, ingredients: ings, portion: Number(customPortion.value) || 1 })
  customName.value = ''
  customIngredients.value = ''
  customPortion.value = 1
}

function applyAiAmount() {
  if (!record.value) return
  const alloc = record.value.member_allocation || []
  record.value.shared_dishes.forEach((d) => {
    const hasAi = alloc.some((a) =>
      (a.dishes || []).some((x) => x.dish_name === d.name && Number(x.amount_g) > 0)
    )
    if (!hasAi) return
    record.value.checked[d.name] = true
    alloc.forEach((a) => {
      const hit = (a.dishes || []).find((x) => x.dish_name === d.name)
      if (hit && Number(hit.amount_g) > 0) {
        d.aiFlags[a.member_id] = true
        d.portions[a.member_id] = undefined
      }
    })
  })
  ElMessage.success('已勾选全部 AI 推荐菜品（各成员将按推荐分量记录，可手动调整）')
}

async function submitFeedback() {
  if (!record.value) return ElMessage.warning('请先选择食谱方案')
  const anyChecked = Object.values(record.value.checked).some(Boolean)
  const anyCustom = customList.value.length > 0
  if (!anyChecked && !anyCustom) return ElMessage.warning('请至少勾选一道实际制作的菜，或补记方案外的菜')

  const items = []
  let hasAiItem = false
  record.value.shared_dishes.forEach((d) => {
    if (!record.value.checked[d.name]) return
    recordMembers().forEach((m) => {
      if (d.aiFlags[m.member_id]) {
        items.push({ member_id: m.member_id, dish_name: d.name })
        hasAiItem = true
      } else if (hasManual(d, m.member_id)) {
        items.push({ member_id: m.member_id, dish_name: d.name, ratio: d.portions[m.member_id] })
      }
    })
  })
  // 方案外的菜：每位成员都按同一份数记录（手动实际值，带主料折算）
  customList.value.forEach((c) => {
    recordMembers().forEach((m) => {
      items.push({
        member_id: m.member_id,
        dish_name: c.name,
        ratio: c.portion,
        custom_ingredients: c.ingredients,
      })
    })
  })
  if (!items.length) return ElMessage.warning('请为勾选的菜品选择「AI 分配」或填写食用比例')

  saving.value = true
  try {
    await http.post('/feedback', {
      family_id: 1,
      recipe_record_id: selectedRecordId.value,
      eaten_date: eatenDate.value,
      meal_type: mealType.value,
      use_ai_amount: hasAiItem,
      items,
    })
    ElMessage.success('反馈已提交，周报将按有效天数统计')
    submitted.value = true
    customList.value = []
    await loadHistory()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function loadHistory() {
  try {
    const { data } = await http.get('/feedback')
    history.value = data.items || []
  } catch (e) {
    /* 忽略 */
  }
}

function memberName(id) {
  const m = membersCache.value.find((x) => x.id === id)
  return m ? m.name : `#${id}`
}

// ===== 时间线视图（纯前端分组，不改后端接口） =====
const recAmountMap = computed(() => {
  const map = new Map() // `${recordId}:${memberId}:${dishName}` -> 推荐克数
  records.value.forEach((rec) => {
    ;(rec.member_allocation || []).forEach((a) => {
      ;(a.dishes || []).forEach((d) => {
        map.set(`${rec.id}:${a.member_id}:${d.dish_name}`, Number(d.amount_g))
      })
    })
  })
  return map
})

const recordDays = computed(() => new Set(history.value.map((h) => h.eaten_date)).size)
const recordMemberCount = computed(() => new Set(history.value.map((h) => h.member_id)).size)
const latestDate = computed(() => {
  const last = history.value[0]
  return last ? last.eaten_date : ''
})

const groupedHistory = computed(() => {
  const byDate = new Map()
  history.value.slice().reverse().forEach((h) => {
    const key = h.eaten_date
    if (!byDate.has(key)) byDate.set(key, { date: key, members: new Map() })
    const grp = byDate.get(key)
    if (!grp.members.has(h.member_id)) grp.members.set(h.member_id, { member_id: h.member_id, items: [] })
    const member = grp.members.get(h.member_id)
    member.items.push({
      dish_name: h.dish_name,
      amount_g: Number(h.amount_g),
      is_ai_recommended: h.is_ai_recommended,
      recAmount: recAmountMap.value.get(`${h.recipe_record_id}:${h.member_id}:${h.dish_name}`),
    })
  })
  return Array.from(byDate.values())
    .sort((a, b) => (a.date < b.date ? 1 : -1))
    .map((grp) => ({
      ...grp,
      dayOfWeek: dayjs(grp.date).format('ddd'),
      members: Array.from(grp.members.values()).map((m) => ({
        ...m,
        items: m.items.sort((x, y) => (x.dish_name < y.dish_name ? -1 : 1)),
      })),
    }))
})

const cmpText = (r) => {
  if (!r.recAmount) return ''
  const diff = Math.round((r.amount_g / r.recAmount) * 100)
  return diff >= 105 ? `超推荐 ${diff - 100}%` : diff <= 95 ? `少 ${100 - diff}%` : '达标'
}
const cmpClass = (r) => {
  if (!r.recAmount) return ''
  const diff = r.amount_g / r.recAmount
  if (diff >= 1.05) return 'cmp-up'
  if (diff <= 0.95) return 'cmp-down'
  return 'cmp-ok'
}

onMounted(async () => {
  await Promise.all([loadMembers(), loadRecords(), loadHistory()])
})
</script>

<style scoped>
.card-section {
  padding: 22px;
}
.step-bar {
  margin-bottom: 4px;
}
.select-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.dish-name {
  font-weight: 600;
  color: var(--hf-ink);
}
.dish-name-sm {
  font-weight: 500;
}
.member-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.member-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--hf-line-soft);
  border: 1px solid var(--hf-line);
  border-radius: 999px;
  transition: all 0.2s ease;
}
.member-cell:hover {
  border-color: var(--hf-primary);
  background: var(--hf-primary-light);
  transform: translateY(-1px);
  box-shadow: var(--hf-shadow-sm);
}
.mname {
  font-size: 12px;
  color: var(--hf-ink-2);
  min-width: 34px;
  font-weight: 600;
}
.unit-hint {
  font-size: 12px;
  color: var(--hf-ink-2);
}
.submit-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px dashed var(--hf-line);
  flex-wrap: wrap;
}
.submit-row .el-button--success {
  min-width: 140px;
  height: 42px;
  font-size: 15px;
  font-weight: 600;
}
.submit-hint {
  font-size: 12px;
  max-width: 560px;
  line-height: 1.6;
  color: var(--hf-ink-3);
}
.amount-text {
  font-weight: 600;
  color: var(--hf-primary-dark);
}
/* 时间线视图 */
.overview-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.ov-card {
  flex: 1;
  min-width: 120px;
  background: var(--hf-line-soft);
  border: 1px solid var(--hf-line);
  border-radius: 10px;
  padding: 12px 14px;
  text-align: center;
}
.ov-card--warn {
  background: #e9f1ec;
  border-color: #e8e9e4;
}
.ov-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--hf-primary-dark);
  font-variant-numeric: tabular-nums;
}
.ov-num--warn {
  color: #24563f;
  font-size: 14px;
  margin-top: 2px;
}
.ov-label {
  font-size: 12px;
  color: var(--hf-ink-3);
  margin-top: 2px;
}
.timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.tl-day {
  border: 1px solid var(--hf-line);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}
.tl-date {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--hf-line-soft);
  font-weight: 600;
  font-size: 13px;
  color: var(--hf-ink);
  border-bottom: 1px solid var(--hf-line);
}
.tl-day-tag {
  font-size: 11px;
  color: var(--hf-ink-3);
  font-weight: 400;
}
.tl-body {
  padding: 8px 14px;
}
.tl-member {
  padding: 6px 0;
  display: flex;
  gap: 10px;
}
.tl-member + .tl-member {
  border-top: 1px dashed var(--hf-line);
}
.tl-member-name {
  min-width: 64px;
  font-weight: 600;
  font-size: 13px;
  color: var(--hf-ink);
  padding-top: 2px;
}
.tl-rows {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tl-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  flex-wrap: wrap;
}
.tl-dish {
  color: var(--hf-ink);
}
.tl-amount {
  font-weight: 600;
  color: var(--hf-primary-dark);
  font-variant-numeric: tabular-nums;
}
.tl-cmp {
  font-size: 11px;
  border-radius: 999px;
  padding: 1px 8px;
}
.cmp-ok {
  color: #2f6b4f;
  background: #e9f1ec;
}
.cmp-up {
  color: #b4464f;
  background: #f7ecec;
}
.cmp-down {
  color: #24563f;
  background: #e9f1ec;
}
.tl-src {
  font-size: 11px;
  border-radius: 999px;
  padding: 1px 8px;
}
.src-manual {
  color: #24563f;
  background: #e9f1ec;
}
.src-ai {
  color: #a87b2a;
  background: #f5f6f2;
}
/* 自定义菜品 */
.custom-dish-box {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed var(--hf-line);
}
.custom-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--hf-ink-2);
  margin-bottom: 10px;
}
.custom-form {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.custom-list {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
