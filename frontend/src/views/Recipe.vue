<template>
  <div class="page-wrap">
    <!-- 页面标题 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">AI 食谱方案</h2>
        <p class="page-sub">
          基于家庭档案与家中食材，AI 生成全家共享一桌菜，并给出每道菜所需食材分量与成员分餐方案。
        </p>
      </div>
    </div>

    <!-- 生成入口（Hero 区） -->
    <div class="glass-card hero-card">
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-title">一键生成全家食谱</div>
          <div class="hero-desc">AI 将综合成员档案、体质忌口与现有食材，推荐最合适的菜品组合</div>
          <div class="hero-controls">
            <span class="control-label">餐次</span>
            <el-select v-model="mealType" style="width: 110px">
              <el-option v-for="o in MEAL_TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
            <span class="control-label">期望菜品数量</span>
            <span class="count-capsule">
              <el-input-number v-model="dishCount" :min="2" :max="10" controls-position="right" />
            </span>
            <el-radio-group v-model="buySupplement">
              <el-radio-button :value="true">现有食材+推荐采购</el-radio-button>
              <el-radio-button :value="false">仅用现有食材</el-radio-button>
            </el-radio-group>
            <el-tag v-if="latestRecordId" type="info" effect="plain" round>
              最近方案 #{{ latestRecordId }}
            </el-tag>
          </div>
        </div>
        <div class="hero-right">
          <el-button type="primary" size="large" :icon="MagicStick" :loading="generating" @click="generate">
            生成食谱方案
          </el-button>
        </div>
      </div>
      <div v-if="gateNote" class="hero-alert">
        <el-alert :title="gateNote" type="info" :closable="false" show-icon />
      </div>
    </div>

    <template v-if="result">
      <!-- 建议采购：缺料 + 营养缺口合并；菜够/无缺料则不出现 -->
      <div v-if="(result.purchase_list || []).length" class="glass-card card-section purchase-card">
        <div class="card-head">
          <span class="section-title"><el-icon><ShoppingCart /></el-icon>建议采购</span>
          <el-tag type="warning" effect="plain" round>{{ result.purchase_list.length }} 项</el-tag>
        </div>
        <el-table :data="result.purchase_list" size="small" border>
          <el-table-column label="食材" min-width="120">
            <template #default="{ row }">
              <span v-if="row.is_must_buy" style="color:#b4464f">★ </span>{{ row.food_name }}
            </template>
          </el-table-column>
          <el-table-column label="建议量" width="110">
            <template #default="{ row }">{{ row.suggest_amount_g }}g</template>
          </el-table-column>
          <el-table-column label="为什么买" min-width="200">
            <template #default="{ row }">{{ row.remark || (row.supplement_nutrient || []).join('、') || '补营养' }}</template>
          </el-table-column>
        </el-table>
        <div class="gap-note">家里的食材直接吃不用重复买；买齐这些食材后，可做的菜会更多。</div>
      </div>

      <div v-if="result.tip" class="glass-card card-section tip-card">
        <el-alert :title="result.tip" type="info" :closable="false" show-icon />
      </div>

      <!-- 共享菜品 -->
      <div class="glass-card card-section">
        <div class="card-head">
          <span class="section-title"><el-icon><Dish /></el-icon>共享菜品</span>
          <el-tag type="primary" effect="plain" round>{{ result.shared_dishes.length }} 道</el-tag>
        </div>
        <el-row :gutter="16">
          <el-col v-for="d in result.shared_dishes" :key="d.name" :xs="24" :sm="12" :md="8">
            <el-card shadow="never" class="dish-card" :body-style="{ padding: '16px' }">
              <div class="dish-name">
                <el-tag :type="d.is_main_dish ? 'primary' : 'success'" size="small" effect="plain" round>
                  {{ d.is_main_dish ? '主菜' : '配菜' }}
                </el-tag>
                <b>{{ d.name }}</b>
              </div>
              <div class="dish-meta">
                <span class="meta-label">食材</span>
                <div class="ingredient-list">
                  <el-tag
                    v-for="(ing, idx) in d.main_ingredients"
                    :key="idx"
                    size="small"
                    effect="plain"
                    class="ing-tag"
                  >
                    {{ ing }}
                  </el-tag>
                  <span v-if="!(d.main_ingredients || []).length" class="text-muted">—</span>
                </div>
              </div>
              <div class="dish-meta" v-if="d.cooking_method">
                <span class="meta-label">做法</span>
                <span>{{ d.cooking_method }}</span>
              </div>
              <div class="dish-meta" v-if="d.note">
                <span class="meta-label">备注</span>
                <span>{{ d.note }}</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 成员个性化食谱 -->
      <div class="glass-card card-section">
        <div class="card-head">
          <span class="section-title"><el-icon><User /></el-icon>成员个性化食谱</span>
          <el-tag type="primary" effect="plain" round>{{ result.member_allocation.length }} 人</el-tag>
        </div>
        <el-row :gutter="16">
          <el-col
            v-for="member in result.member_allocation"
            :key="member.member_id"
            :xs="24"
            :sm="12"
            :md="8"
          >
            <el-card shadow="never" class="member-card" :body-style="{ padding: '16px' }">
              <div class="member-head">
                <el-avatar :size="36" class="member-avatar">
                  {{ member.member_name.charAt(0) }}
                </el-avatar>
                <div class="member-info">
                  <div class="member-name">{{ member.member_name }}</div>
                  <div class="member-sub">个性化分餐方案</div>
                </div>
              </div>
              <div class="member-dishes">
                <div
                  v-for="d in member.dishes"
                  :key="d.dish_name"
                  class="member-dish-row"
                >
                  <div class="member-dish-name">{{ d.dish_name }}</div>
                  <el-tag size="small" type="warning" effect="plain" round>
                    {{ d.amount_g }}g
                  </el-tag>
                </div>
                <div v-if="!(member.dishes || []).length" class="text-muted">暂未分配</div>
              </div>
              <div v-if="(member.cooking_tips || []).length" class="member-tips">
                <div class="member-adv-title">烹饪提示</div>
                <div v-for="(t, i) in member.cooking_tips" :key="i" class="tips-line">
                  <el-icon color="#a87b2a"><InfoFilled /></el-icon>
                  {{ t }}
                </div>
              </div>
              <div v-if="(member.intake_advantage || []).length" class="member-adv">
                <div class="member-adv-title">摄入优点</div>
                <div v-for="(a, i) in member.intake_advantage" :key="i" class="adv-line">
                  <el-icon color="#2f6b4f"><CircleCheckFilled /></el-icon>
                  {{ a }}
                </div>
              </div>
              <div v-if="(member.nutrition_gap || []).length" class="member-gap">
                <div class="member-gap-title">营养缺口</div>
                <div class="tag-list">
                  <el-tooltip
                    v-for="g in member.nutrition_gap"
                    :key="g.nutrient"
                    :content="`一天目标 ${fmtNum(g.rni)}，这一餐提供 ${fmtNum(g.actual)}，缺口 ${fmtNum(g.gap_ratio)}%`"
                    placement="top"
                  >
                    <el-tag :type="tagType(g.gap_ratio)" size="small" effect="plain">
                      {{ g.nutrient_name }} 缺 {{ fmtNum(g.gap_ratio) }}%
                    </el-tag>
                  </el-tooltip>
                </div>
                <div v-if="hasGapAdvice(member.nutrition_gap)" class="gap-advice">
                  <div v-for="g in member.nutrition_gap" :key="g.nutrient" class="gap-advice-line">
                    <template v-if="(g.advice || []).length">
                      <b>{{ g.nutrient_name }}：</b>建议补 {{ g.advice.join('、') }}
                    </template>
                  </div>
                </div>
                <div class="gap-note">缺口口径：一天目标 vs 这一餐提供，不代表全天</div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

    </template>

    <div v-else class="glass-card empty-hint">
      <div class="empty-art"><FoodIcons name="soup" :size="120" /></div>
      <div class="empty-title">当前还没有生成过食谱方案</div>
      <div class="empty-sub">请先确保已录入至少一位成员，然后点击上方「生成食谱方案」。</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, Dish, InfoFilled, MagicStick, ShoppingCart, User } from '@element-plus/icons-vue'
import http, { MEAL_TYPE_OPTIONS } from '../api'
import FoodIcons from '../components/FoodIcons.vue'

const dishCount = ref(4)
const mealType = ref('dinner')
const buySupplement = ref(true)
const generating = ref(false)
const result = ref(null)
const latestRecordId = ref(null)
const gateNote = ref('')

const tagType = (ratio) => {
  const r = Number(ratio)
  if (r > 30) return 'danger'
  if (r > 10) return 'warning'
  return 'info'
}

const fmtNum = (v) => {
  const n = Number(v ?? 0)
  return Number.isInteger(n) ? n : n.toFixed(1)
}

const hasGapAdvice = (gaps) => (gaps || []).some((g) => (g.advice || []).length)

async function generate() {
  generating.value = true
  gateNote.value = ''
  try {
    const { data } = await http.post('/recipes/generate', {
      family_id: 1,
      dish_count: dishCount.value,
      meal_type: mealType.value,
      buy_supplement: buySupplement.value,
    })
    latestRecordId.value = data.record_id
    result.value = data.result
  } catch (e) {
    gateNote.value = e.message
    ElMessage.error(e.message)
  } finally {
    generating.value = false
  }
}

async function loadLatestRecord() {
  try {
    const { data } = await http.get('/recipes/records')
    if (data.items && data.items.length) {
      const rec = data.items[0]
      latestRecordId.value = rec.id
      if (rec.member_allocation && rec.member_allocation.length) {
        result.value = {
          shared_dishes: rec.shared_dishes || [],
          member_allocation: rec.member_allocation || [],
          purchase_list: rec.purchase_list || [],
        }
      }
    }
  } catch (e) {
    /* 首次进入无记录属正常 */
  }
}

onMounted(loadLatestRecord)
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
  font-size: 22px;
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
.control-label {
  font-size: 13px;
  color: var(--hf-ink-2);
}
/* 菜品数量胶囊 */
.count-capsule {
  display: inline-flex;
  align-items: center;
  padding: 4px 6px;
  background: var(--hf-primary-light);
  border: 1px solid rgba(47, 107, 79, 0.15);
  border-radius: 999px;
}
.count-capsule .el-input-number {
  --el-input-height: 30px;
}
.hero-right {
  flex-shrink: 0;
}
.hero-alert {
  margin-top: 16px;
}
.dish-card {
  margin-bottom: 12px;
  border: 1px solid var(--hf-line);
  border-radius: var(--hf-radius-sm);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.dish-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--hf-shadow);
}
.dish-name {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 15px;
}
.dish-meta {
  font-size: 12px;
  color: var(--hf-ink-2);
  margin-top: 4px;
  display: flex;
  gap: 6px;
  line-height: 1.5;
}
.meta-label {
  color: var(--hf-ink-3);
  flex-shrink: 0;
  min-width: 32px;
}
.ingredient-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ing-tag {
  border-radius: 999px;
}
.ing-amount {
  color: var(--hf-primary-dark);
  font-weight: 600;
  margin-left: 2px;
}
.member-name {
  font-weight: 600;
  color: var(--hf-ink);
}
.member-card {
  margin-bottom: 12px;
  border: 1px solid var(--hf-line);
  border-radius: var(--hf-radius-sm);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.member-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--hf-shadow);
}
.member-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.member-avatar {
  background: linear-gradient(135deg, var(--hf-primary), var(--hf-primary-dark));
  color: #fff;
  font-weight: 600;
}
.member-info {
  flex: 1;
}
.member-sub {
  font-size: 12px;
  color: var(--hf-ink-3);
}
.member-dishes {
  border-top: 1px dashed var(--hf-line);
  padding-top: 10px;
}
.member-dish-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
}
.member-dish-name {
  color: var(--hf-ink);
  font-weight: 500;
}
.member-adv {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--hf-line);
}
.member-adv-title,
.member-gap-title {
  font-size: 12px;
  color: var(--hf-ink-3);
  margin-bottom: 4px;
}
.member-gap {
  margin-top: 8px;
}
.gap-advice {
  margin-top: 6px;
  padding: 8px 10px;
  background: var(--hf-line-soft);
  border-radius: 8px;
}
.gap-advice-line {
  font-size: 12.5px;
  color: var(--hf-ink-2);
  line-height: 1.6;
}
.gap-note {
  margin-top: 6px;
  font-size: 11px;
  color: var(--hf-ink-3);
}
.member-tips {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--hf-line);
}
.tips-line {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  line-height: 1.6;
  font-size: 13px;
  margin-bottom: 4px;
  color: #24563f;
}
.adv-line {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  line-height: 1.6;
  font-size: 13px;
  margin-bottom: 4px;
}
/* 空态插画引导 */
.empty-art {
  margin: 6px 0 16px;
  filter: drop-shadow(0 10px 18px rgba(47, 107, 79, 0.22));
  animation: empty-bob 3.2s ease-in-out infinite;
}
@keyframes empty-bob {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--hf-ink);
}
.empty-sub {
  color: var(--hf-ink-3);
  font-size: 12px;
  margin-top: 4px;
}
</style>
