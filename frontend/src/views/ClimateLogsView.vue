<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const list = ref([])
const zones = ref([])
const error = ref('')
const editingId = ref(null)
const filterZoneId = ref('')
const includeVoided = ref(false)
const voidStats = ref({ voidedCount: 0, validCount: 0 })

function localInputValue(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const form = reactive({
  zoneId: '',
  recordedAt: localInputValue(),
  tempC: 24,
  humidityPct: 65,
  parUmol: 300,
  co2Ppm: 600,
})

function resetForm() {
  editingId.value = null
  form.zoneId = zones.value[0]?.id || ''
  form.recordedAt = localInputValue()
  form.tempC = 24
  form.humidityPct = 65
  form.parUmol = 300
  form.co2Ppm = 600
}

async function loadZones() {
  const { data } = await api.get('/zones/')
  zones.value = data.results || data
  if (!form.zoneId && zones.value.length) form.zoneId = zones.value[0].id
}

async function load() {
  error.value = ''
  try {
    const params = {}
    if (filterZoneId.value) params.zoneId = filterZoneId.value
    if (includeVoided.value) params.includeVoided = 'true'
    const { data } = await api.get('/climate-logs/', { params })
    list.value = data.results || data
    await loadVoidStats()
  } catch {
    error.value = '加载气候日志失败'
  }
}

async function loadVoidStats() {
  try {
    const params = {}
    if (filterZoneId.value) params.zoneId = filterZoneId.value
    const { data } = await api.get('/climate-logs/void-stats/', { params })
    voidStats.value = data
  } catch {
    // 统计仅为辅助展示，失败不阻断列表
  }
}

function edit(row) {
  editingId.value = row.id
  form.zoneId = row.zoneId
  form.recordedAt = localInputValue(new Date(row.recordedAt))
  form.tempC = Number(row.tempC)
  form.humidityPct = Number(row.humidityPct)
  form.parUmol = Number(row.parUmol)
  form.co2Ppm = Number(row.co2Ppm)
}

async function save() {
  error.value = ''
  if (form.humidityPct < 20 || form.humidityPct > 100) {
    error.value = '湿度 humidityPct 须在 20～100'
    return
  }
  const payload = {
    zoneId: Number(form.zoneId),
    recordedAt: new Date(form.recordedAt).toISOString(),
    tempC: form.tempC,
    humidityPct: form.humidityPct,
    parUmol: form.parUmol,
    co2Ppm: form.co2Ppm,
  }
  try {
    if (editingId.value) {
      await api.put(`/climate-logs/${editingId.value}/`, payload)
    } else {
      await api.post('/climate-logs/', payload)
    }
    resetForm()
    await load()
  } catch (e) {
    error.value = JSON.stringify(e.response?.data || '保存失败')
  }
}

async function voidRow(row) {
  const reason = prompt(`作废第 ${row.id} 条气候记录，请输入作废原因（至少 6 个字）：`)
  if (reason === null) return
  if (reason.trim().length < 6) {
    error.value = '作废原因去空白后至少 6 个字'
    return
  }
  error.value = ''
  try {
    await api.post(`/climate-logs/${row.id}/void/`, { voidReason: reason.trim() })
    await load()
  } catch (e) {
    if (e.response?.status === 409) {
      error.value = e.response.data?.detail || '该记录已作废'
    } else {
      error.value = JSON.stringify(e.response?.data || '作废失败')
    }
    await load()
  }
}

async function remove(id) {
  if (!confirm('确认删除该气候日志？')) return
  await api.delete(`/climate-logs/${id}/`)
  await load()
}

onMounted(async () => {
  await loadZones()
  await load()
})
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>气候日志</h1>
        <p>记录温湿度、PAR、CO₂；湿度须 ∈ [20, 100]。已作废记录默认不进入列表与看板统计</p>
      </div>
      <div class="actions">
        <label style="display:flex;align-items:center;gap:6px;white-space:nowrap">
          <input v-model="includeVoided" type="checkbox" @change="load" />
          包含已作废
        </label>
        <select v-model="filterZoneId" @change="load">
          <option value="">全部分区</option>
          <option v-for="z in zones" :key="z.id" :value="z.id">
            {{ z.greenhouseName }} / {{ z.zoneCode }}
          </option>
        </select>
      </div>
    </div>

    <p style="color:var(--muted);margin:0 0 12px">
      有效记录 {{ voidStats.validCount }} 条 · 已作废 {{ voidStats.voidedCount }} 条
      （有效数与默认列表一致，已作废数为全部作废行数）
    </p>

    <div class="panel">
      <h3 style="margin-top:0">{{ editingId ? '编辑日志' : '新建日志' }}</h3>
      <div class="form-grid">
        <label>
          分区
          <select v-model="form.zoneId">
            <option v-for="z in zones" :key="z.id" :value="z.id">
              {{ z.greenhouseName }} / {{ z.zoneCode }}
            </option>
          </select>
        </label>
        <label>记录时间<input v-model="form.recordedAt" type="datetime-local" /></label>
        <label>温度 ℃<input v-model.number="form.tempC" type="number" step="0.01" /></label>
        <label>湿度 %<input v-model.number="form.humidityPct" type="number" step="0.01" min="20" max="100" /></label>
        <label>PAR µmol<input v-model.number="form.parUmol" type="number" step="0.01" /></label>
        <label>CO₂ ppm<input v-model.number="form.co2Ppm" type="number" step="0.01" /></label>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="actions" style="margin-top:12px">
        <button class="btn" @click="save">保存</button>
        <button v-if="editingId" class="btn ghost" @click="resetForm">取消编辑</button>
      </div>
    </div>

    <div class="panel">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>温室/分区</th>
            <th>温度</th>
            <th>湿度</th>
            <th>PAR</th>
            <th>CO₂</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.id" :class="{ 'row-voided': row.voided }">
            <td>{{ new Date(row.recordedAt).toLocaleString() }}</td>
            <td>{{ row.greenhouseName }} / {{ row.zoneCode }}</td>
            <td>{{ row.tempC }}</td>
            <td>{{ row.humidityPct }}</td>
            <td>{{ row.parUmol }}</td>
            <td>{{ row.co2Ppm }}</td>
            <td>
              <span v-if="row.voided" class="badge-voided">
                已作废 · {{ new Date(row.voidedAt).toLocaleString() }}
                <template v-if="row.voidReason">（{{ row.voidReason }}）</template>
              </span>
              <span v-else class="badge-valid">有效</span>
            </td>
            <td class="actions">
              <template v-if="!row.voided">
                <button class="btn ghost" @click="edit(row)">编辑</button>
                <button class="btn warn" @click="voidRow(row)">作废</button>
                <button class="btn danger" @click="remove(row.id)">删除</button>
              </template>
              <span v-else style="color:var(--muted)">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.row-voided {
  opacity: 0.6;
}
.badge-voided {
  color: #b04a3a;
  font-size: 12px;
}
.badge-valid {
  color: var(--leaf-deep, #3d6b3a);
  font-size: 12px;
}
</style>
