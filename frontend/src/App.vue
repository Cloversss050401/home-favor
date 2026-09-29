<template>
  <el-container class="app-shell">
    <BGDeco />
    <el-aside width="240px" class="app-aside">
      <div class="brand-box">
        <div class="brand-logo">
          <FoodIcons name="pan" :size="32" />
        </div>
        <div class="brand-text">
          <div class="brand-name">家味</div>
          <div class="brand-sub">家庭 AI 食谱推荐</div>
        </div>
      </div>

      <div class="nav-label">工作台</div>
      <el-menu
        :default-active="active"
        class="nav-menu"
        @select="onSelect"
      >
        <el-menu-item index="members">
          <el-icon><UserFilled /></el-icon>
          <span>家庭成员档案</span>
        </el-menu-item>
        <el-menu-item index="pantry">
          <el-icon><ShoppingCart /></el-icon>
          <span>家中食材</span>
        </el-menu-item>
        <el-menu-item index="recipe">
          <el-icon><MagicStick /></el-icon>
          <span>AI 食谱方案</span>
        </el-menu-item>
        <el-menu-item index="feedback">
          <el-icon><EditPen /></el-icon>
          <span>做菜反馈</span>
        </el-menu-item>
        <el-menu-item index="report">
          <el-icon><DataAnalysis /></el-icon>
          <span>每周营养报告</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-foot">
        <div class="foot-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>先录入成员与食材，再生成食谱</span>
        </div>
      </div>
      <div class="aside-deco">
        <FoodIcons name="orange" :size="20" />
        <FoodIcons name="carrot" :size="20" />
        <FoodIcons name="broccoli" :size="20" />
        <FoodIcons name="milk" :size="20" />
        <FoodIcons name="tomato" :size="20" />
      </div>
    </el-aside>

    <el-main class="app-main">
      <component :is="currentView" />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import FoodIcons from './components/FoodIcons.vue'
import BGDeco from './components/BGDeco.vue'
import Members from './views/Members.vue'
import Pantry from './views/Pantry.vue'
import Recipe from './views/Recipe.vue'
import Feedback from './views/Feedback.vue'
import Report from './views/Report.vue'

const active = ref(localStorage.getItem('hf_active_tab') || 'members')
const currentView = computed(() => {
  const map = {
    members: Members,
    pantry: Pantry,
    recipe: Recipe,
    feedback: Feedback,
    report: Report,
  }
  return map[active.value] || Members
})

function onSelect(index) {
  active.value = index
  localStorage.setItem('hf_active_tab', index)
}

watch(active, () => {
  document.querySelector('.app-main')?.scrollTo(0, 0)
})
</script>

<style scoped>
.app-shell {
  height: 100vh;
}

.app-aside {
  position: relative;
  z-index: 1;
  background: var(--hf-card);
  border-right: 1px solid var(--hf-line);
  display: flex;
  flex-direction: column;
  padding: 22px 14px;
}

.brand-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 10px 22px;
}

.brand-logo {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: var(--hf-primary-light);
  border: 1px solid var(--hf-line);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: var(--hf-shadow-sm);
}

.brand-name {
  font-weight: 700;
  font-size: 16px;
  color: var(--hf-ink);
  line-height: 1.2;
}

.brand-sub {
  color: var(--hf-ink-3);
  font-size: 12px;
  margin-top: 3px;
}

.nav-label {
  font-size: 11px;
  color: var(--hf-ink-3);
  font-weight: 600;
  letter-spacing: 0.12em;
  padding: 0 14px 10px;
  text-transform: uppercase;
}

.nav-menu {
  border-right: none;
  background: transparent;
  flex: 1;
}

/* 菜单胶囊化 */
.nav-menu .el-menu-item {
  position: relative;
  border-radius: 999px;
  margin: 4px 0;
  height: 46px;
  line-height: 46px;
  color: var(--hf-ink-2);
  font-size: 14px;
  font-weight: 500;
  transition: all 0.22s ease;
  padding-left: 20px !important;
}

.nav-menu .el-menu-item:hover {
  background: var(--hf-primary-light);
  color: var(--hf-primary);
}

/* 激活态：浅色渐变底 + 主色文字 + 左侧渐变指示条 */
.nav-menu .el-menu-item.is-active {
  background: linear-gradient(90deg, var(--hf-primary-light) 0%, var(--hf-gold-light) 100%);
  color: var(--hf-primary-dark);
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(47, 107, 79, 0.12);
}

.nav-menu .el-menu-item.is-active::before {
  content: "";
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 20px;
  border-radius: 3px;
  background: var(--hf-primary);
}

.nav-menu .el-menu-item.is-active .el-icon {
  color: var(--hf-primary);
}

.aside-foot {
  padding: 14px 10px 4px;
  border-top: 1px solid var(--hf-line-soft);
  margin-top: 12px;
}

.foot-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: var(--hf-ink-3);
  line-height: 1.5;
}

.foot-tip .el-icon {
  margin-top: 1px;
  flex-shrink: 0;
}

.aside-deco {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 14px 2px;
  opacity: 0.85;
}

.app-main {
  position: relative;
  z-index: 1;
  padding: 0;
  overflow-y: auto;
  background: transparent;
}
</style>
