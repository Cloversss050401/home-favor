<template>
  <div class="page-wrap">
    <!-- 页面标题 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">每周营养报告</h2>
        <p class="page-sub">
          按天汇总每位成员的实际摄入；没有反馈的餐次按当天最后一次生成的方案估算，对照 DRIs 计算达标率，输出每位成员的问题与建议。
        </p>
      </div>
    </div>

    <!-- 生成入口（Hero 区） -->
    <div class="glass-card hero-card">
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-title">生成本周营养报告</div>
          <div class="hero-desc">选择统计周期，AI 将分析每位成员的营养素摄入达标情况与改进建议</div>
          <div class="hero-controls">
            <el-date-picker
              v-model="weekRange"
              type="daterange"
              range-separator="至"
              start-placeholder="本周开始"
              end-placeholder="本周结束"
              value-format="YYYY-MM-DD"
            />
          </div>
        </div>
        <div class="hero-right">
          <el-button type="primary" size="large" :icon="DataAnalysis" :loading="generating" @click="generateReport">
            生成周报
          </el-button>
        </div>
      </div>
      <div v-if="currentReport" class="hero-alert">
        <el-alert
          :title="`周报 #${currentReport.id} · ${currentReport.week_start} 至 ${currentReport.week_end} · 有效 ${effDays} 天（实际 ${reportStats.actual} / 估算 ${reportStats.est}）`"
          type="success"
          :closable="false"
          show-icon
        />
      </div>
    </div>

    <!-- 历史周报 -->
    <div class="glass-card card-section">
      <div class="card-head">
        <span class="section-title"><el-icon><Clock /></el-icon>历史周报</span>
        <el-button
          v-if="currentReport"
          type="success"
          :icon="Download"
          :loading="exporting"
          @click="exportReport"
        >
          导出 Excel
        </el-button>
      </div>
      <el-table :data="reports" stripe empty-text="暂无周报，请先生成">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="统计周期" min-width="220">
          <template #default="{ row }">{{ row.week_start }} 至 {{ row.week_end }}</template>
        </el-table-column>
        <el-table-column label="有效天数" width="100">
          <template #default="{ row }">
            <span class="cell-mono day-badge">{{ row.report_data?.effective_days ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" min-width="150">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="170" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewReport(row)">查看</el-button>
            <el-button link type="danger" @click="deleteReport(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 报告明细 -->
    <div v-if="currentReport" class="glass-card card-section">
      <div class="card-head">
        <span class="section-title"><el-icon><Tickets /></el-icon>报告明细</span>
        <el-tag v-if="reportStats.estDays > 0" type="warning" effect="plain" round>
          含估算：{{ reportStats.estDays }} 天
        </el-tag>
      </div>

      <!-- 统计概览：分档口径 -->
      <div class="stats-row">
        <div class="stats-card">
          <div class="stats-num">{{ reportStats.effective }}</div>
          <div class="stats-label">有效统计天数</div>
        </div>
        <div class="stats-card stats-card--actual">
          <div class="stats-num">{{ reportStats.actual }}</div>
          <div class="stats-label">手动实际记录</div>
        </div>
        <div class="stats-card stats-card--est">
          <div class="stats-num">{{ reportStats.est }}</div>
          <div class="stats-label">AI 估算（按最后方案）</div>
        </div>
        <div class="stats-card stats-card--no">
          <div class="stats-num">{{ reportStats.noData }}</div>
          <div class="stats-label">无数据（不硬凑）</div>
        </div>
      </div>
      <div v-if="reportStats.est > 0" class="stats-note">
        本周期 {{ reportStats.est }} 天没有做菜反馈，按当天最后一次食谱方案估算；结论仅供参考，最好补录实际吃食。
      </div>

      <!-- 本周必买采购（连续缺口历史联动） -->
      <div v-if="mustBuyList.length" class="must-buy-card">
        <div class="must-buy-title"><el-icon><ShoppingCart /></el-icon>本周必买采购（连续 {{ gapDays }} 天缺营养触发）</div>
        <div class="must-buy-grid">
          <div v-for="(it, i) in mustBuyList" :key="i" class="must-buy-item">
            <span class="must-star">★</span>
            <span class="must-food">{{ it.food }}</span>
            <span class="must-meta">补{{ it.nutrient_name }} · {{ it.nutrients.join('、') }}</span>
            <span class="must-who">为 {{ it.members.join('、') }}</span>
          </div>
        </div>
        <div class="must-buy-note">连续多天同一种营养缺口时升级为必买项，并自动合并进采购清单。</div>
      </div>

      <div v-for="m in currentReport.report_data.members || []" :key="m.member_id" class="member-block">
        <div class="member-head">
          <div class="member-avatar">
            <el-icon><UserFilled /></el-icon>
          </div>
          <div class="member-name">{{ m.member_name }}</div>
        </div>
        <el-table :data="m.nutrients" border size="small">
          <el-table-column prop="nutrient_name" label="营养素" min-width="110" />
          <el-table-column label="RNI/天" width="100">
            <template #default="{ row }"><span class="cell-mono">{{ Number(row.rni_per_day) }}</span></template>
          </el-table-column>
          <el-table-column label="有效天数" width="90">
            <template #default="{ row }"><span class="cell-mono">{{ row.effective_days }}</span></template>
          </el-table-column>
          <el-table-column label="累计摄入" width="110">
            <template #default="{ row }"><span class="cell-mono">{{ Number(row.total_intake) }}</span></template>
          </el-table-column>
          <el-table-column label="日均摄入" width="110">
            <template #default="{ row }"><span class="cell-mono">{{ Number(row.daily_avg) }}</span></template>
          </el-table-column>
          <el-table-column label="达标率" width="120">
            <template #default="{ row }">
              <div class="rate-cell">
                <span class="cell-mono rate-num" :style="{ color: rateColor(row.rate) }">{{ Number(row.rate) }}%</span>
                <el-progress
                  :percentage="Math.min(100, Math.round(row.rate))"
                  :color="rateColor(row.rate)"
                  :show-text="false"
                  :stroke-width="6"
                />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.exceeded ? 'danger' : Number(row.rate) < 100 ? 'warning' : 'success'" size="small" effect="plain">
                {{ row.exceeded ? '超标' : Number(row.rate) < 100 ? '缺口' : '达标' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="累计缺口" width="110">
            <template #default="{ row }"><span class="cell-mono">{{ Number(row.gap) }}</span></template>
          </el-table-column>
        </el-table>
        <div class="member-problem" v-if="m.problem_summary && m.problem_summary.length">
          <el-icon color="#a87b2a"><WarningFilled /></el-icon>
          <span>{{ m.problem_summary.join('；') }}</span>
        </div>
      </div>

      <div v-if="(currentReport.report_data.weekly_tips || []).length" class="tips-card">
        <div class="tips-title"><el-icon><Promotion /></el-icon>下周饮食建议</div>
        <ul>
          <li v-for="(t, i) in currentReport.report_data.weekly_tips" :key="i">{{ t }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, DataAnalysis, Download, Promotion, ShoppingCart, Tickets, WarningFilled, UserFilled } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import http from '../api'

const weekRange = ref([])
const reports = ref([])
const currentReport = ref(null)
const generating = ref(false)
const exporting = ref(false)

const fmt = (v) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '—')
const effDays = computed(() => currentReport.value?.report_data?.effective_days ?? 0)
const gapDays = computed(() => currentReport.value?.report_data?.stats?.gap_days ?? 3)

const reportStats = computed(() => {
  const s = currentReport.value?.report_data?.stats || {}
  return {
    effective: s.effective_days ?? effDays.value,
    actual: s.actual_days ?? 0,
    est: s.est_days ?? 0,
    noData: s.no_data_days ?? 0,
  }
})

// 必买项：按食材合并去重（同食材多成员/多营养素合并展示）
const mustBuyList = computed(() => {
  const raw = currentReport.value?.report_data?.must_buy_items || []
  const map = new Map()
  raw.forEach((it) => {
    const key = it.food
    if (!map.has(key)) {
      map.set(key, { food: it.food, members: [], nutrients: [], nutrientNames: new Set() })
    }
    const entry = map.get(key)
    if (!entry.members.includes(it.member_name)) entry.members.push(it.member_name)
    if (!entry.nutrients.includes(it.nutrient_name)) entry.nutrients.push(it.nutrient_name)
  })
  return Array.from(map.values()).map((e) => ({ ...e, nutrient_name: e.nutrients[0] }))
})

const rateColor = (r) => {
  const v = Number(r)
  if (v < 60) return '#b4464f'
  if (v < 100) return '#a87b2a'
  return '#2f6b4f'
}

function defaultWeek() {
  const today = dayjs()
  const monday = today.startOf('week').add(1, 'day')
  const sunday = monday.add(6, 'day')
  return [monday.format('YYYY-MM-DD'), sunday.format('YYYY-MM-DD')]
}

async function loadReports() {
  try {
    const { data } = await http.get('/reports')
    reports.value = data.items || []
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function generateReport() {
  if (!weekRange.value || weekRange.value.length !== 2) {
    return ElMessage.warning('请选择统计周期')
  }
  generating.value = true
  try {
    const { data } = await http.post('/reports/generate', {
      family_id: 1,
      week_start: weekRange.value[0],
      week_end: weekRange.value[1],
      generate_type: 0,
    })
    currentReport.value = data
    ElMessage.success('周报已生成')
    await loadReports()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    generating.value = false
  }
}

function viewReport(row) {
  currentReport.value = row
  weekRange.value = [row.week_start, row.week_end]
}

async function exportReport() {
  if (!currentReport.value) return
  exporting.value = true
  try {
    const { data } = await http.get('/reports/export', { params: { report_id: currentReport.value.id } })
    if (!data.ok) return ElMessage.warning('导出失败')
    window.open(`/exports/${data.file_name}`, '_blank')
    ElMessage.success('周报已导出（两个 sheet：明细 + 问题与建议）')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    exporting.value = false
  }
}

async function deleteReport(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除周报 #${row.id}（${row.week_start} 至 ${row.week_end}）？删除后不可恢复。`,
      '删除周报',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return // 用户取消
  }
  try {
    await http.delete(`/reports/${row.id}`)
    ElMessage.success('周报已删除')
    if (currentReport.value && currentReport.value.id === row.id) {
      currentReport.value = null
    }
    await loadReports()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(() => {
  weekRange.value = defaultWeek()
  loadReports()
})
</script>

<style scoped>
.card-section {
  padding: 22px;
}
.hero-card {
  padding: 28px 32px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(233, 241, 236, 0.7) 100%);
}
.hero-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.hero-left {
  flex: 1;
  min-width: 280px;
}
.hero-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--hf-ink);
  margin-bottom: 6px;
}
.hero-desc {
  font-size: 13px;
  color: var(--hf-ink-2);
  margin-bottom: 16px;
  line-height: 1.6;
}
.hero-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.hero-right {
  flex-shrink: 0;
}
.hero-alert {
  margin-top: 16px;
}
.day-badge {
  display: inline-block;
  min-width: 28px;
  padding: 2px 8px;
  background: var(--hf-primary-light);
  color: var(--hf-primary-dark);
  border-radius: 6px;
  font-weight: 600;
  text-align: center;
}
.member-block {
  background: var(--hf-line-soft);
  border: 1px solid var(--hf-line);
  border-radius: var(--hf-radius-sm);
  padding: 16px 18px;
  margin-top: 16px;
}
.member-block:first-of-type {
  margin-top: 0;
}
.member-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.member-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--hf-primary) 0%, var(--hf-gold) 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 10px rgba(47, 107, 79, 0.25);
}
.member-head .member-name {
  font-weight: 600;
  font-size: 15px;
  color: var(--hf-ink);
}
.rate-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rate-num {
  font-weight: 600;
  font-size: 13px;
}
.member-problem {
  margin-top: 10px;
  font-size: 13px;
  color: #a87b2a;
  background: rgba(168, 123, 42, 0.06);
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  line-height: 1.6;
}
/* 下周建议：独立高亮卡片 */
.tips-card {
  margin-top: 20px;
  padding: 20px 24px;
  border-radius: var(--hf-radius-sm);
  background: linear-gradient(135deg, rgba(47, 107, 79, 0.1) 0%, rgba(47, 107, 79, 0.06) 100%);
  border: 1px solid rgba(47, 107, 79, 0.25);
}
.tips-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: var(--hf-primary-dark);
  margin-bottom: 10px;
}
.tips-title .el-icon {
  color: var(--hf-gold);
}
.tips-card ul {
  margin: 0;
  padding-left: 20px;
}
.tips-card li {
  line-height: 1.9;
  color: var(--hf-ink-2);
  font-size: 13px;
}
/* 统计分档概览 */
.stats-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.stats-card {
  flex: 1;
  min-width: 110px;
  background: var(--hf-line-soft);
  border: 1px solid var(--hf-line);
  border-radius: 10px;
  padding: 12px 14px;
  text-align: center;
}
.stats-card--actual {
  background: #e9f1ec;
  border-color: #e8e9e4;
}
.stats-card--est {
  background: #f5f6f2;
  border-color: #e8e9e4;
}
.stats-card--no {
  background: #f5f6f2;
  border-color: #e0e0e0;
}
.stats-num {
  font-size: 22px;
  font-weight: 700;
  color: var(--hf-primary-dark);
  font-variant-numeric: tabular-nums;
}
.stats-label {
  font-size: 12px;
  color: var(--hf-ink-3);
  margin-top: 2px;
}
.stats-note {
  font-size: 12px;
  color: #a87b2a;
  background: rgba(168, 123, 42, 0.06);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 14px;
  line-height: 1.6;
}
/* 必买采购卡 */
.must-buy-card {
  margin-top: 16px;
  padding: 16px 20px;
  border-radius: var(--hf-radius-sm);
  background: linear-gradient(135deg, rgba(168, 123, 42, 0.08) 0%, rgba(168, 123, 42, 0.06) 100%);
  border: 1px solid rgba(168, 123, 42, 0.3);
}
.must-buy-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
  color: #24563f;
  margin-bottom: 10px;
}
.must-buy-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.must-buy-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  border: 1px solid #e8e9e4;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12.5px;
}
.must-star {
  color: #b4464f;
  font-weight: 700;
}
.must-food {
  font-weight: 600;
  color: var(--hf-ink);
}
.must-meta {
  color: #24563f;
}
.must-who {
  color: var(--hf-ink-3);
}
.must-buy-note {
  margin-top: 8px;
  font-size: 11px;
  color: var(--hf-ink-3);
}
</style>
