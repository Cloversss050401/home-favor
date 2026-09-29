import axios from 'axios'

// 统一 axios 实例：开发期走 Vite 代理（/api -> 127.0.0.1:8001，以后端 .env 的 SERVER_PORT 为准）
const http = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 统一错误弹层（由各页面自行捕获时不用此默认提示）
http.interceptors.response.use(
  (res) => res,
  (err) => {
    const data = err?.response?.data || {}
    // FastAPI 422 校验错误（detail 为数组）
    if (Array.isArray(data.detail)) {
      return Promise.reject(new Error(data.detail.map((m) => m.msg).join('；')))
    }
    const msg =
      data.detail || data.message || err?.message || '请求失败，请检查后端服务'
    return Promise.reject(new Error(msg))
  }
)

export default http

/* ================= 枚举字典（与 src/config/constants.py 对齐） ================= */

export const ROLE_OPTIONS = [
  { value: 'adult', label: '成人' },
  { value: 'elders', label: '长辈' },
  { value: 'child', label: '儿童' },
  { value: 'teen', label: '青少年' },
  { value: 'baby', label: '婴幼儿' },
  { value: 'pregnant', label: '孕妈妈' },
]

export const GENDER_OPTIONS = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
  { value: 'other', label: '不指定' },
]

export const ACTIVITY_OPTIONS = [
  { value: 'sedentary', label: '久坐少动' },
  { value: 'light', label: '轻度活动' },
  { value: 'moderate', label: '中度活动' },
  { value: 'heavy', label: '重度活动' },
]

export const DIET_GOAL_OPTIONS = [
  { value: 'normal', label: '均衡膳食' },
  { value: 'slim', label: '减脂' },
  { value: 'muscle', label: '健身增肌' },
  { value: 'pregnant', label: '孕妈营养' },
  { value: 'baby', label: '婴幼儿辅食' },
  { value: 'elderly', label: '老年营养' },
  { value: 'vegetarian', label: '素食' },
]

// 附加需求（多选，叠加在主目标之上，不互相覆盖）
export const DIETARY_NEED_OPTIONS = [
  { value: 'vegetarian', label: '素食' },
  { value: 'low_salt', label: '低盐' },
  { value: 'low_sugar', label: '控糖' },
  { value: 'low_fat', label: '低脂' },
  { value: 'iron_supp', label: '补铁' },
  { value: 'high_fiber', label: '高纤维' },
]

// 餐次
export const MEAL_TYPE_OPTIONS = [
  { value: 'breakfast', label: '早餐' },
  { value: 'lunch', label: '午餐' },
  { value: 'dinner', label: '晚餐' },
  { value: 'snack', label: '加餐' },
]

export const CONSTITUTION_OPTIONS = [
  { value: 'balanced', label: '平和质' },
  { value: 'qi_deficiency', label: '气虚质' },
  { value: 'yang_deficiency', label: '阳虚质（体寒）' },
  { value: 'yin_deficiency', label: '阴虚质' },
  { value: 'phlegm_dampness', label: '痰湿质' },
  { value: 'blood_stasis', label: '血瘀质' },
  { value: 'damp_heat', label: '湿热质' },
  { value: 'qi_stagnation', label: '气郁质' },
  { value: 'special', label: '特禀质' },
  { value: 'cold', label: '体质偏寒' },
  { value: 'hot', label: '体质偏热' },
  { value: 'qi-deficiency', label: '气虚（前端）' },
  { value: 'yin-deficiency', label: '阴虚（前端）' },
  { value: 'dampness', label: '痰湿/湿热' },
  { value: 'stomach', label: '脾胃虚寒' },
]

export const HEALTH_OPTIONS = [
  { value: 'none', label: '无' },
  { value: 'hypertension', label: '高血压' },
  { value: 'diabetes', label: '糖尿病' },
  { value: 'hyperlipidemia', label: '高血脂' },
  { value: 'gout', label: '痛风' },
  { value: 'kidney', label: '肾病' },
  { value: 'anemia', label: '贫血倾向' },
  { value: 'low-protein', label: '优质蛋白不足' },
  { value: 'low-calcium', label: '钙摄入不足' },
  { value: 'low-vita', label: '维生素A不足' },
]

export const ALLERGEN_OPTIONS = [
  { value: 'peanut', label: '花生' },
  { value: 'egg', label: '鸡蛋' },
  { value: 'shellfish', label: '海鲜/贝类' },
  { value: 'milk', label: '牛奶' },
  { value: 'soy', label: '大豆' },
  { value: 'gluten', label: '麸质' },
  { value: 'seafood', label: '海鲜（前端）' },
  { value: 'nuts', label: '花生/坚果' },
  { value: 'spicy', label: '辛辣' },
  { value: 'nightshade', label: '番茄/茄果' },
]

export const labelOf = (options, value) => {
  const hit = options.find((o) => o.value === value)
  return hit ? hit.label : value
}

export const labelsOf = (options, values) =>
  (values || []).map((v) => labelOf(options, v)).join('、') || '—'

/* ================= 个人中心（一期单用户模拟，无鉴权） ================= */

export const profileApi = {
  /** 获取个人资料（后端不存在时自动初始化默认账号） */
  get: () => http.get('/profile/info'),
  /** 更新签名、手机号 */
  update: (payload) => http.put('/profile/info', payload),
  /** 上传头像，返回 { avatar_url } */
  uploadAvatar: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/profile/avatar', fd)
  },
  /** 修改密码：old_password + new_password */
  changePassword: (payload) => http.post('/profile/change-pwd', payload),
}