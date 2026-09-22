<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const list = ref([])
const zones = ref([])
const error = ref('')
const editingId = ref(null)
const filterZoneId = ref('')
const includeVoided = ref(false)
const voidStats = ref(null)

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
  } catch {
    error.value = '加载气候日志失败'
  }
}

async function loadVoidStats() {
  try {
    const params = {}
    if (filterZoneId.value) params.zoneId = filterZoneId.value
    const { data } = await api.get('/climate-logs/stats/void/', { params })
    voidStats.value = data
  } catch {
    voidStats.value = null
  }
}

async function refresh() {
  await Promise.all([load(), loadVoidStats()])
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
    await refresh()
  } catch (e) {
    error.value = JSON.stringify(e.response?.data || '保存失败')
  }
}

async function voidRow(row) {
  const input = prompt(
    `作废 #${row.id}：请输入作废原因（可留空；填写时去空白后至少 6 个字）`,
    ''
  )
  if (input === null) return
  const reason = input.trim()
  if (reason.length > 0 && reason.length < 6) {
    error.value = '作废原因去空白后至少 6 个字'
    return
  }
  error.value = ''
  try {
    await api.post(`/climate-logs/${row.id}/void/`, { reason })
    await refresh()
  } catch (e) {
    if (e.response?.status === 409) {
      error.value = e.response.data?.detail || '该记录已作废，不能重复作废'
    } else {
      error.value = JSON.stringify(e.response?.data || '作废失败')
    }
  }
}

async function remove(id) {
  if (!confirm('确认删除该气候日志？')) return
  await api.delete(`/climate-logs/${id}/`)
  await refresh()
}

onMounted(async () => {
  await loadZones()
  await refresh()
})
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>气候日志</h1>
        <p>记录温湿度、PAR、CO₂；湿度须 ∈ [20, 100]；异常记录可作废而非删除</p>
      </div>
      <div class="actions">
        <label style="display:flex;align-items:center;gap:6px">
          <input v-model="includeVoided" type="checkbox" @change="refresh" />
          包含已作废
        </label>
        <select v-model="filterZoneId" @change="refresh">
          <option value="">全部分区</option>
          <option v-for="z in zones" :key="z.id" :value="z.id">
            {{ z.greenhouseName }} / {{ z.zoneCode }}
          </option>
        </select>
      </div>
    </div>

    <div class="panel" v-if="voidStats">
      <p style="margin:0;color:var(--muted)">
        有效记录 <strong>{{ voidStats.validTotal }}</strong> 条 ·
        已作废 <strong>{{ voidStats.voidedTotal }}</strong> 条
        （有效数与默认列表一致，已作废数为勾选「包含已作废」后标记的行数）
      </p>
    </div>

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
          <tr v-for="row in list" :key="row.id" :class="{ 'row-voided': row.isVoided }">
            <td>{{ new Date(row.recordedAt).toLocaleString() }}</td>
            <td>{{ row.greenhouseName }} / {{ row.zoneCode }}</td>
            <td>{{ row.tempC }}</td>
            <td>{{ row.humidityPct }}</td>
            <td>{{ row.parUmol }}</td>
            <td>{{ row.co2Ppm }}</td>
            <td>
              <span v-if="row.isVoided" class="badge voided" :title="row.voidReason">
                已作废{{ row.voidedAt ? ' · ' + new Date(row.voidedAt).toLocaleString() : '' }}
              </span>
              <span v-else class="badge done">有效</span>
            </td>
            <td class="actions">
              <template v-if="!row.isVoided">
                <button class="btn ghost" @click="edit(row)">编辑</button>
                <button class="btn secondary" @click="voidRow(row)">作废</button>
                <button class="btn danger" @click="remove(row.id)">删除</button>
              </template>
              <span v-else class="void-reason">{{ row.voidReason || '（未填原因）' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.row-voided td {
  color: var(--muted);
  text-decoration: line-through;
}
.row-voided td .badge,
.row-voided td .void-reason {
  text-decoration: none;
}
.badge.voided {
  background: #efe2dd;
  color: #8a4b34;
}
.void-reason {
  color: var(--muted);
  font-size: 12px;
}
</style>
