<template>
  <div class="page-wrap">
    <!-- 页面标题 + 主操作 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">家庭成员档案</h2>
        <p class="page-sub">
          录入每位家人的角色、身高体重、体质与过敏忌口，AI 生成食谱时会按每人营养需求自动分餐（最多 8 人）。
        </p>
      </div>
      <el-button type="primary" size="large" :icon="Plus" @click="openCreate">
        新增成员
      </el-button>
    </div>

    <!-- 统计条 -->
    <div class="stat-bar">
      <div class="stat-item">
        <div class="stat-num">{{ members.length }}</div>
        <div class="stat-label">已录入成员</div>
      </div>
      <div class="stat-split"></div>
      <div class="stat-item">
        <div class="stat-num">{{ 8 - members.length }}</div>
        <div class="stat-label">剩余名额</div>
      </div>
      <div class="stat-split"></div>
      <div class="stat-item">
        <div class="stat-num">{{ allergenCount }}</div>
        <div class="stat-label">需关注过敏原</div>
      </div>
    </div>

    <!-- 成员列表 -->
    <div class="glass-card card-section">
      <div class="card-head">
        <span class="section-title"><el-icon><User /></el-icon>成员列表</span>
        <el-tag type="info" effect="plain" round>{{ members.length }} / 8</el-tag>
      </div>

      <el-table :data="members" stripe empty-text="暂无成员，点击右上角「新增成员」开始录入">
        <el-table-column prop="name" label="姓名" width="110">
          <template #default="{ row }">
            <span class="member-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="primary" effect="plain">{{ labelOf(ROLE_OPTIONS, row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="身高/体重" min-width="130">
          <template #default="{ row }">
            <span class="cell-mono">{{ row.height_cm != null ? Number(row.height_cm) : '—' }} cm / {{ row.weight_kg != null ? Number(row.weight_kg) : '—' }} kg</span>
          </template>
        </el-table-column>
        <el-table-column label="年龄" width="80">
          <template #default="{ row }">
            <span class="cell-mono">{{ row.age != null ? Number(row.age) : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="性别" width="80">
          <template #default="{ row }">{{ labelOf(GENDER_OPTIONS, row.gender) }}</template>
        </el-table-column>
        <el-table-column label="饮食目标" width="110">
          <template #default="{ row }">{{ labelOf(DIET_GOAL_OPTIONS, row.diet_goal) }}</template>
        </el-table-column>
        <el-table-column label="体质" min-width="160">
          <template #default="{ row }">
            <div class="tag-list">
              <el-tag v-for="c in row.constitution || []" :key="c" size="small" type="success" effect="plain">
                {{ labelOf(CONSTITUTION_OPTIONS, c) }}
              </el-tag>
              <span v-if="!(row.constitution || []).length" class="text-muted">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="健康状况" min-width="160">
          <template #default="{ row }">
            <div class="tag-list">
              <el-tag v-for="h in row.health_conditions || []" :key="h" size="small" type="warning" effect="plain">
                {{ labelOf(HEALTH_OPTIONS, h) }}
              </el-tag>
              <span v-if="!(row.health_conditions || []).length" class="text-muted">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="过敏原" min-width="170">
          <template #default="{ row }">
            <div class="tag-list">
              <el-tag v-for="a in row.allergens || []" :key="a" size="small" type="danger" effect="plain">
                {{ labelOf(ALLERGEN_OPTIONS, a) }}
              </el-tag>
              <span v-if="!(row.allergens || []).length" class="text-muted">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="avoid" label="其他忌口" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.avoid || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="removeMember(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑成员档案' : '新增成员档案'"
      width="780px"
      destroy-on-close
      top="5vh"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="96px"
        label-position="right"
      >
        <!-- 基本信息 -->
        <div class="form-block">
          <div class="form-block-title">
            <span class="block-bar"></span>基本信息
          </div>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="姓名" prop="name">
                <el-input v-model="form.name" maxlength="20" placeholder="如：妈妈" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="家庭角色">
                <el-select v-model="form.role" clearable placeholder="选择角色" style="width: 100%">
                  <el-option v-for="o in ROLE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="年龄">
                <el-input-number
                  v-model="form.age"
                  :min="0"
                  :max="120"
                  :precision="2"
                  :step="1"
                  controls-position="right"
                  style="width: 100%"
                />
                <div class="text-muted" style="font-size: 12px">婴儿可填小数，如 0.67</div>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="性别">
                <el-radio-group v-model="form.gender">
                  <el-radio v-for="o in GENDER_OPTIONS" :key="o.value" :value="o.value">
                    {{ o.label }}
                  </el-radio>
                </el-radio-group>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="饮食目标">
                <el-select v-model="form.diet_goal" clearable placeholder="均衡膳食" style="width: 100%">
                  <el-option v-for="o in DIET_GOAL_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="附加需求">
                <el-select v-model="form.dietary_needs" multiple collapse-tags placeholder="叠加约束，可多选" style="width: 100%">
                  <el-option v-for="o in DIETARY_NEED_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="身高">
                <el-input-number v-model="form.height_cm" :min="30" :max="250" :precision="1" controls-position="right" placeholder="cm" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="体重">
                <el-input-number v-model="form.weight_kg" :min="1" :max="300" :precision="1" controls-position="right" placeholder="kg" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="运动量">
                <el-select v-model="form.activity" clearable placeholder="轻度活动" style="width: 100%">
                  <el-option v-for="o in ACTIVITY_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 健康档案 -->
        <div class="form-block">
          <div class="form-block-title">
            <span class="block-bar block-bar--mint"></span>健康档案
          </div>
          <el-form-item label="体质类型">
            <el-select v-model="form.constitution" multiple collapse-tags placeholder="可多选" style="width: 100%">
              <el-option v-for="o in CONSTITUTION_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="健康状况">
            <el-select v-model="form.health_conditions" multiple collapse-tags placeholder="可多选" style="width: 100%">
              <el-option v-for="o in HEALTH_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="过敏原">
            <el-select
              v-model="form.allergens"
              multiple
              collapse-tags
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入自定义过敏原"
              style="width: 100%"
            >
              <el-option v-for="o in ALLERGEN_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="其他忌口">
            <el-input
              v-model="form.avoid"
              type="textarea"
              :rows="2"
              maxlength="200"
              show-word-limit
              placeholder="如：不吃香菜、不吃肥肉、忌辛辣……"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMember">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, User } from '@element-plus/icons-vue'
import http, {
  ROLE_OPTIONS, ACTIVITY_OPTIONS, GENDER_OPTIONS, DIET_GOAL_OPTIONS, DIETARY_NEED_OPTIONS,
  CONSTITUTION_OPTIONS, HEALTH_OPTIONS, ALLERGEN_OPTIONS, labelOf,
} from '../api'

const members = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formRef = ref(null)

const allergenCount = computed(() =>
  members.value.reduce((sum, m) => sum + (m.allergens?.length || 0), 0)
)

const emptyForm = () => ({
  name: '',
  role: '',
  height_cm: undefined,
  weight_kg: undefined,
  activity: 'light',
  age: undefined,
  gender: 'other',
  diet_goal: '',
  dietary_needs: [],
  constitution: [],
  health_conditions: [],
  allergens: [],
  dietary_restrictions: [],
  avoid: '',
})

const form = reactive(emptyForm())

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

async function loadMembers() {
  try {
    const { data } = await http.get('/members')
    members.value = data.items || []
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function openCreate() {
  if (members.value.length >= 8) {
    ElMessage.warning('单个家庭最多 8 位成员')
    return
  }
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, emptyForm(), {
    name: row.name,
    role: row.role || '',
    height_cm: row.height_cm != null ? Number(row.height_cm) : undefined,
    weight_kg: row.weight_kg != null ? Number(row.weight_kg) : undefined,
    activity: row.activity || 'light',
    age: row.age != null ? Number(row.age) : undefined,
    gender: row.gender || 'other',
    diet_goal: row.diet_goal || '',
    dietary_needs: row.dietary_needs || [],
    constitution: row.constitution || [],
    health_conditions: row.health_conditions || [],
    allergens: row.allergens || [],
    dietary_restrictions: row.dietary_restrictions || [],
    avoid: row.avoid || '',
  })
  dialogVisible.value = true
}

async function saveMember() {
  await formRef.value?.validate().catch(() => Promise.reject(new Error('表单校验未通过')))
  saving.value = true
  try {
    const payload = { ...form }
    if (editingId.value) {
      await http.put(`/members/${editingId.value}`, payload)
      ElMessage.success('成员档案已更新')
    } else {
      await http.post('/members', payload)
      ElMessage.success('成员档案已保存')
    }
    dialogVisible.value = false
    await loadMembers()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

function removeMember(row) {
  ElMessageBox.confirm(`确定删除成员「${row.name}」吗？历史食谱与报告将保留。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
    .then(async () => {
      try {
        await http.delete(`/members/${row.id}`)
        ElMessage.success('已删除（逻辑删除，历史数据保留）')
        await loadMembers()
      } catch (e) {
        ElMessage.error(e.message)
      }
    })
    .catch(() => {})
}

onMounted(loadMembers)
</script>

<style scoped>
.card-section {
  padding: 22px;
}
.stat-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  background: linear-gradient(135deg, var(--hf-primary-light) 0%, var(--hf-gold-light) 100%);
  border: 1px solid var(--hf-line);
  border-radius: var(--hf-radius);
  padding: 18px 28px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: var(--hf-primary-dark);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.stat-label {
  font-size: 12px;
  color: var(--hf-ink-2);
}
.stat-split {
  width: 1px;
  height: 32px;
  background: var(--hf-line);
}
.member-name {
  font-weight: 600;
  color: var(--hf-ink);
}
/* 表单分区块 */
.form-block {
  background: var(--hf-line-soft);
  border: 1px solid var(--hf-line);
  border-radius: var(--hf-radius-sm);
  padding: 16px 18px;
  margin-bottom: 16px;
}
.form-block:last-child {
  margin-bottom: 0;
}
.form-block-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 14px;
  color: var(--hf-primary-dark);
  margin: 0 0 14px;
}
.block-bar {
  display: inline-block;
  width: 4px;
  height: 16px;
  border-radius: 3px;
  background: linear-gradient(180deg, var(--hf-primary) 0%, var(--hf-gold) 100%);
}
.block-bar--mint {
  background: linear-gradient(180deg, var(--hf-gold) 0%, var(--hf-primary) 100%);
}
</style>
