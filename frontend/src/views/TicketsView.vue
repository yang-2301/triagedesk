<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import { useAuthStore } from "../stores/auth";
import type { Ticket } from "../types";

const auth = useAuthStore();
const router = useRouter();

const tickets = ref<Ticket[]>([]);
const loading = ref(false);
const error = ref("");

const filters = reactive({
  status: "", priority: "", category: "", q: "", page: 1,
});

const canCreate = ref(false);
const showForm = ref(false);
const form = reactive({ title: "", description: "" });
const formBusy = ref(false);
const formError = ref("");
const lastCreated = ref<Ticket | null>(null);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) if (v) params.set(k, String(v));
    tickets.value = await api.get<Ticket[]>(`/api/tickets?${params}`);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

watch(filters, load);
onMounted(load);

function open(t: Ticket) {
  router.push(`/tickets/${t.id}`);
}

async function createTicket() {
  formBusy.value = true;
  formError.value = "";
  lastCreated.value = null;
  try {
    const t = await api.post<Ticket>("/api/tickets", {
      title: form.title, description: form.description,
    });
    lastCreated.value = t;
    form.title = form.description = "";
    showForm.value = false;
    await load();
  } catch (e: any) {
    formError.value = e.message;
  } finally {
    formBusy.value = false;
  }
}
</script>

<template>
  <div>
    <div class="head">
      <h1>Tickets</h1>
      <button class="primary" @click="showForm = !showForm">New ticket</button>
    </div>

    <div v-if="showForm" class="card newform">
      <h2>New ticket</h2>
      <p class="muted">
        Leave category/priority blank — the AI triager decides them on submit.
      </p>
      <input v-model="form.title" placeholder="Short summary, e.g. 'Charged twice on renewal'" />
      <textarea v-model="form.description" rows="4"
                placeholder="What happened? Include anything an agent would need." />
      <p v-if="formError" class="error-text">{{ formError }}</p>
      <div class="row">
        <button class="primary" :disabled="formBusy || form.title.length < 3 || form.description.length < 5"
                @click="createTicket">
          {{ formBusy ? "Triaging…" : "Submit & auto-triage" }}
        </button>
        <button @click="showForm = false">Cancel</button>
      </div>
    </div>

    <div v-if="lastCreated" class="card triage-flash">
      <strong>AI triage result:</strong>
      <span class="badge" :class="'priority-' + lastCreated.priority">{{ lastCreated.priority }}</span>
      <span class="badge">{{ lastCreated.category }}</span>
      <span class="muted">confidence {{ lastCreated.triage_confidence }} · source {{ lastCreated.triage_source }}</span>
    </div>

    <div class="card">
      <div class="filters">
        <select v-model="filters.status">
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <select v-model="filters.priority">
          <option value="">All priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="normal">Normal</option>
          <option value="low">Low</option>
        </select>
        <select v-model="filters.category">
          <option value="">All categories</option>
          <option value="billing">Billing</option>
          <option value="bug">Bug</option>
          <option value="feature">Feature</option>
          <option value="account">Account</option>
          <option value="general">General</option>
        </select>
        <input v-model="filters.q" placeholder="Search title / description…" class="search" />
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
      <p v-if="loading" class="muted">Loading…</p>

      <table v-if="!loading && tickets.length">
        <thead>
          <tr><th>Title</th><th>Status</th><th>Priority</th><th>Category</th><th>Created</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in tickets" :key="t.id" class="row-link" @click="open(t)">
            <td>
              {{ t.title }}
              <div v-if="t.triage_source === 'ai'" class="muted">
                AI: {{ t.category }} · conf {{ t.triage_confidence }}
              </div>
            </td>
            <td><span class="badge" :class="'status-' + t.status">{{ t.status.replace('_', ' ') }}</span></td>
            <td><span class="badge" :class="'priority-' + t.priority">{{ t.priority }}</span></td>
            <td class="muted">{{ t.category }}</td>
            <td class="muted">{{ t.created_at.slice(0, 16).replace('T', ' ') }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="!loading" class="muted">No tickets match.</p>
    </div>
  </div>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.newform { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }
.newform .row { display: flex; gap: 8px; }
.filters { display: grid; grid-template-columns: repeat(3, 1fr) 2fr; gap: 8px; margin-bottom: 12px; }
.triage-flash { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; border-left: 3px solid var(--accent); }
</style>
