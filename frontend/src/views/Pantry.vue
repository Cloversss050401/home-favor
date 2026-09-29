<template>
  <div class="page-wrap">
    <!-- 页面标题 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">家中食材</h2>
        <p class="page-sub">
          支持文字 / 批量两种录入方式；识别结果需人工确认后才入库，避免误录。
        </p>
      </div>
      <div class="head-actions">
        <el-button :icon="Refresh" circle @click="loadIngredients" title="刷新" />
        <el-button type="danger" plain :icon="Delete" @click="clearAll">清空食材</el-button>
      </div>
    </div>

    <!-- 录入方式选择 -->
    <div class="glass-card card-section">
      <div class="card-head">
        <span class="section-title"><el-icon><CirclePlus /></el-icon>选择录入方式</span>
      </div>

      <div class="input-methods">
        <div
          v-for="m in methods"
          :key="m.key"
          class="method-card"
          :class="{ active: activeTab === m.key }"
          @click="activeTab = m.key"
        >
          <div class="method-icon" :style="{ background: m.bg, color: m.color }">
            <el-icon :size="20"><component :is="m.icon" /></el-icon>
          </div>
          <div class="method-info">
            <div class="method-name">{{ m.label }}</div>
            <div class="method-desc">{{ m.desc }}</div>
          </div>
        </div>
      </div>

      <!-- 文字录入 -->
      <div v-show="activeTab === 'text'" class="method-panel">
        <el-input
          v-model="textInput"
          type="textarea"
          :rows="3"
          placeholder="如：番茄 500g / 鸡胸肉，可一次输入多条，用逗号或换行分隔"
          clearable
        />
        <div class="panel-actions">
          <el-button type="primary" :icon="Search" :loading="recognizing" @click="recognizeText">
            识别
          </el-button>
          <el-button :icon="Select" :loading="recognizing" @click="recognizeBatch">批量识别（多行）</el-button>
        </div>
      </div>

      <!-- 待确认列表 -->
      <div v-if="pending.length" class="pending-block">
        <div class="pending-head">
          <span class="section-title" style="font-size: 14px">
            <el-icon><Warning /></el-icon>
            识别结果（共 {{ pending.length }} 条）
          </span>
          <span class="text-muted" style="font-size: 12px">请核对名称与重量后确认入库</span>
        </div>
        <el-table :data="pending" size="small" border>
          <el-table-column prop="name" label="食材名称" min-width="160">
            <template #default="{ row }">
              <el-input v-model="row.name" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="可用重量 (g)" width="200">
            <template #default="{ row }">
              <el-input-number
                v-model="row.available_weight"
                :min="0"
                :precision="1"
                size="small"
                controls-position="right"
                style="width: 100%"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" @click="pending.splice($index, 1)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pending-actions">
          <el-button type="success" :icon="Check" :loading="confirming" @click="confirmPending">
            确认入库（{{ pending.length }} 条）
          </el-button>
          <el-button @click="pending = []">清空待确认</el-button>
        </div>
      </div>
    </div>

    <!-- 家中现有食材 -->
    <div class="glass-card card-section">
      <div class="card-head">
        <span class="section-title"><el-icon><ShoppingCart /></el-icon>家中现有食材</span>
        <el-tag type="info" effect="plain" round>{{ ingredients.length }} 种</el-tag>
      </div>

      <el-table :data="ingredients" stripe empty-text="还没有食材，请先在上方录入">
        <el-table-column prop="name" label="食材名称" min-width="150">
          <template #default="{ row }">
            <span class="ing-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="可用重量" width="160">
          <template #default="{ row }">
            <el-input-number
              v-model="row.available_weight"
              :min="0"
              :precision="1"
              size="small"
              controls-position="right"
              style="width: 100%"
              @change="updateIngredient(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="weight_unit" label="单位" width="80" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.available_weight ? 'success' : 'info'" size="small" effect="plain">
              {{ row.available_weight ? '有存量' : '仅标记' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" min-width="160">
          <template #default="{ row }">{{ fmt(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="danger" @click="deleteIngredient(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Check, CirclePlus, Delete, Refresh, Search, Select, Warning, ShoppingCart, Document,
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import http from '../api'

const methods = [
  { key: 'text', label: '文字录入', desc: '手动输入食材名称与重量', icon: Document, bg: '#e9f1ec', color: '#2f6b4f' },
]

const activeTab = ref('text')
const textInput = ref('')
const pending = ref([])
const ingredients = ref([])
const recognizing = ref(false)
const confirming = ref(false)

const fmt = (v) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '—')

function applyRecognized(list) {
  pending.value = (list || []).map((it) => ({
    name: it.name,
    available_weight: it.available_weight != null ? Number(it.available_weight) : undefined,
  }))
  if (!pending.value.length) ElMessage.warning('未识别到食材')
}

async function recognizeText() {
  const name = textInput.value.trim()
  if (!name) return ElMessage.warning('请输入食材文本')
  recognizing.value = true
  try {
    const { data } = await http.post('/ingredients/text', { name })
    applyRecognized(data.recognized)
    textInput.value = ''
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    recognizing.value = false
  }
}

async function recognizeBatch() {
  const lines = textInput.value
    .split(/[\n,，;；]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (!lines.length) return ElMessage.warning('请输入至少一条食材文本')
  recognizing.value = true
  try {
    const { data } = await http.post('/ingredients/text/batch', lines)
    applyRecognized(data.recognized)
    textInput.value = ''
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    recognizing.value = false
  }
}

async function confirmPending() {
  const items = pending.value
    .map((it) => ({
      name: it.name.trim(),
      available_weight: it.available_weight ?? null,
    }))
    .filter((it) => it.name)
  if (!items.length) return ElMessage.warning('待确认列表为空或名称未填写')
  confirming.value = true
  try {
    const { data } = await http.post('/ingredients/confirm', { items })
    ElMessage.success(`已入库 ${data.affected} 种食材`)
    pending.value = []
    await loadIngredients()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    confirming.value = false
  }
}

async function loadIngredients() {
  try {
    const { data } = await http.get('/ingredients')
    ingredients.value = (data.items || []).map((it) => ({
      ...it,
      available_weight: it.available_weight != null ? Number(it.available_weight) : undefined,
    }))
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function updateIngredient(row) {
  try {
    await http.put(`/ingredients/${row.id}`, {
      available_weight: row.available_weight ?? null,
    })
  } catch (e) {
    ElMessage.error(e.message)
    loadIngredients()
  }
}

function deleteIngredient(row) {
  ElMessageBox.confirm(`删除食材「${row.name}」？`, '删除确认', { type: 'warning' })
    .then(async () => {
      try {
        await http.delete(`/ingredients/${row.id}`)
        ElMessage.success('已删除')
        await loadIngredients()
      } catch (e) {
        ElMessage.error(e.message)
      }
    })
    .catch(() => {})
}

function clearAll() {
  ElMessageBox.confirm('确定清空全家所有食材吗？此操作不可撤销。', '清空确认', {
    type: 'warning',
    confirmButtonText: '清空',
  })
    .then(async () => {
      try {
        const { data } = await http.post('/ingredients/clear')
        ElMessage.success(`已清空 ${data.affected} 条`)
        await loadIngredients()
      } catch (e) {
        ElMessage.error(e.message)
      }
    })
    .catch(() => {})
}

onMounted(loadIngredients)
</script>

<style scoped>
.card-section {
  padding: 22px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.input-methods {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 22px;
}
.method-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 1.5px solid var(--hf-line);
  border-radius: var(--hf-radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}
.method-card:hover {
  border-color: var(--hf-primary);
  transform: translateY(-2px);
  box-shadow: var(--hf-shadow-sm);
}
.method-card.active {
  border-color: var(--hf-primary);
  background: var(--hf-primary-light);
  box-shadow: 0 0 0 3px rgba(47, 107, 79, 0.12);
}
.method-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.method-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--hf-ink);
}
.method-desc {
  font-size: 12px;
  color: var(--hf-ink-2);
  margin-top: 2px;
}
.method-panel {
  padding: 18px;
  background: var(--hf-line-soft);
  border-radius: var(--hf-radius-sm);
}
.panel-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
}
.method-tip {
  margin-top: 12px;
  font-size: 12px;
}
.pending-block {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px dashed var(--hf-line);
}
.pending-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.pending-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}
.ing-name {
  font-weight: 500;
  color: var(--hf-ink);
}
</style>
