<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";
import { Chart, registerables } from "chart.js";
import { api } from "../api";
import type { Dashboard } from "../types";

Chart.register(...registerables);

const data = ref<Dashboard | null>(null);
const error = ref("");

onMounted(async () => {
  try {
    data.value = await api.get<Dashboard>("/api/dashboard");
    await nextTick(); // canvas exists only after the v-if re-render flushes
    renderTrend();
  } catch (e: any) {
    error.value = e.message;
  }
});

function renderTrend() {
  const el = document.getElementById("trend") as HTMLCanvasElement | null;
  if (!el || !data.value) return;
  new Chart(el, {
    type: "line",
    data: {
      labels: data.value.trend.map((d) => d.date.slice(5)),
      datasets: [
        { label: "Created", data: data.value.trend.map((d) => d.created),
          borderColor: "#2563eb", backgroundColor: "#dbeafe", tension: .3, fill: true },
        { label: "Resolved", data: data.value.trend.map((d) => d.resolved),
          borderColor: "#16a34a", backgroundColor: "#dcfce7", tension: .3, fill: true },
      ],
    },
    options: { scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
}
</script>

<template>
  <div>
    <h1>Dashboard</h1>
    <p v-if="error" class="error-text">{{ error }}</p>

    <template v-if="data">
      <div class="kpis">
        <div class="card kpi">
          <span class="muted">Total tickets</span>
          <strong>{{ data.total }}</strong>
        </div>
        <div class="card kpi">
          <span class="muted">Open</span>
          <strong>{{ data.by_status["open"] ?? 0 }}</strong>
        </div>
        <div class="card kpi" :class="{ bad: data.sla_breach_count > 0 }">
          <span class="muted">SLA breaches</span>
          <strong>{{ data.sla_breach_count }}</strong>
          <span class="muted">{{ Math.round(data.sla_breach_rate * 100) }}% of volume</span>
        </div>
        <div class="card kpi">
          <span class="muted">Median first response</span>
          <strong>{{ data.median_first_response_hours ?? "—" }}<small>h</small></strong>
        </div>
      </div>

      <div class="charts">
        <div class="card">
          <h2>Created vs resolved — last 7 days</h2>
          <canvas id="trend" height="120" />
        </div>
        <div class="card">
          <h2>By category</h2>
          <table>
            <tbody>
              <tr v-for="(n, c) in data.by_category" :key="c">
                <td class="muted">{{ c }}</td>
                <td><div class="bar"><div class="fill" :style="{ width: (n / data.total * 100) + '%' }" /></div></td>
                <td>{{ n }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card" v-if="data.breached_tickets.length">
        <h2>SLA breaches — act now</h2>
        <table>
          <thead><tr><th>Ticket</th><th>Priority</th><th>Created</th></tr></thead>
          <tbody>
            <tr v-for="t in data.breached_tickets" :key="t.id">
              <td>{{ t.title }}</td>
              <td><span class="badge" :class="'priority-' + t.priority">{{ t.priority }}</span></td>
              <td class="muted">{{ t.created_at.slice(0, 16).replace('T', ' ') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi { display: flex; flex-direction: column; gap: 2px; }
.kpi strong { font-size: 24px; }
.kpi.bad strong { color: var(--danger); }
.charts { display: grid; grid-template-columns: 3fr 2fr; gap: 16px; margin-bottom: 16px; }
.bar { background: #eef1f5; border-radius: 4px; height: 10px; overflow: hidden; min-width: 120px; }
.fill { background: var(--accent); height: 100%; }
td { padding: 6px 8px; }
</style>
