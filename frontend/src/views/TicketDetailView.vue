<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { useAuthStore } from "../stores/auth";
import type { Ticket, Comment } from "../types";

const route = useRoute();
const auth = useAuthStore();
const ticketId = route.params.id as string;

const ticket = ref<Ticket | null>(null);
const comments = ref<Comment[]>([]);
const error = ref("");
const replyBody = ref("");
const internal = ref(false);
const busy = ref(false);
const replyError = ref("");
const statusError = ref("");

const isStaff = computed(() => auth.isStaff);

const NEXT_ACTIONS: Record<string, { to: string; label: string }[]> = {
  open: [
    { to: "in_progress", label: "Start working" },
    { to: "closed", label: "Close without action" },
  ],
  in_progress: [
    { to: "resolved", label: "Mark resolved" },
    { to: "open", label: "Re-open" },
  ],
  resolved: [
    { to: "closed", label: "Close" },
    { to: "in_progress", label: "Re-open" },
  ],
  closed: [],
};

onMounted(async () => {
  try {
    ticket.value = await api.get<Ticket>(`/api/tickets/${ticketId}`);
    comments.value = await api.get<Comment[]>(`/api/tickets/${ticketId}/comments`);
  } catch (e: any) {
    error.value = e.message;
  }
});

async function sendReply() {
  busy.value = true;
  replyError.value = "";
  try {
    await api.post(`/api/tickets/${ticketId}/comments`, {
      body: replyBody.value, is_internal: internal.value,
    });
    replyBody.value = "";
    comments.value = await api.get<Comment[]>(`/api/tickets/${ticketId}/comments`);
  } catch (e: any) {
    replyError.value = e.message;
  } finally {
    busy.value = false;
  }
}

async function transition(to: string) {
  statusError.value = "";
  try {
    ticket.value = await api.post<Ticket>(`/api/tickets/${ticketId}/status`, { status: to });
  } catch (e: any) {
    statusError.value = e.message;
  }
}

function authorName(id: string): string {
  if (auth.auth && id === auth.auth.user.id) return auth.name;
  return id;
}

const statusButtons = computed(() => (ticket.value ? NEXT_ACTIONS[ticket.value.status] ?? [] : []));
</script>

<template>
  <p v-if="error" class="error-text">{{ error }}</p>

  <div v-else-if="ticket" class="layout">
    <div class="main card">
      <div class="ticket-head">
        <h1>{{ ticket.title }}</h1>
        <span class="badge" :class="'status-' + ticket.status">{{ ticket.status.replace('_', ' ') }}</span>
        <span class="badge" :class="'priority-' + ticket.priority">{{ ticket.priority }}</span>
        <span class="badge category">{{ ticket.category }}</span>
      </div>
      <p class="muted">
        #{{ ticket.id }} · created {{ ticket.created_at.slice(0, 16).replace('T', ' ') }}
        <template v-if="ticket.first_response_at">
          · first response {{ ticket.first_response_at.slice(11, 16) }} UTC
        </template>
      </p>
      <p class="description">{{ ticket.description }}</p>

      <h2>Conversation</h2>
      <div class="timeline">
        <div v-for="c in comments" :key="c.id" class="comment" :class="{ internal: c.is_internal }">
          <div class="meta">
            <strong>{{ authorName(c.author_id) }}</strong>
            <span v-if="c.is_internal" class="badge internal">internal note</span>
            <span class="muted">{{ c.created_at.slice(0, 16).replace('T', ' ') }}</span>
          </div>
          <p>{{ c.body }}</p>
        </div>
        <p v-if="!comments.length" class="muted">No replies yet.</p>
      </div>

      <div class="reply">
        <textarea v-model="replyBody" rows="3" placeholder="Write a reply…" />
        <div class="row">
          <label v-if="isStaff" class="internal-toggle">
            <input v-model="internal" type="checkbox" /> internal note (not visible to customer)
          </label>
          <button class="primary" :disabled="busy || !replyBody.trim()" @click="sendReply">
            {{ busy ? "Sending…" : "Send" }}
          </button>
        </div>
        <p v-if="replyError" class="error-text">{{ replyError }}</p>
      </div>
    </div>

    <aside class="side">
      <div class="card">
        <h2>AI triage</h2>
        <div class="triage-grid">
          <span class="muted">Category</span><strong>{{ ticket.category }}</strong>
          <span class="muted">Priority</span><strong>{{ ticket.priority }}</strong>
          <span class="muted">Confidence</span><strong>{{ ticket.triage_confidence ?? "—" }}</strong>
          <span class="muted">Source</span><strong>{{ ticket.triage_source }}</strong>
        </div>
        <template v-if="ticket.suggested_reply && isStaff">
          <p class="muted" style="margin-top: 10px">Suggested reply:</p>
          <p class="suggested">{{ ticket.suggested_reply }}</p>
          <button @click="replyBody = ticket.suggested_reply!">Use as draft</button>
        </template>
      </div>

      <div v-if="isStaff" class="card">
        <h2>Workflow</h2>
        <p v-if="statusError" class="error-text">{{ statusError }}</p>
        <div class="actions">
          <button v-for="a in statusButtons" :key="a.to" @click="transition(a.to)">
            {{ a.label }}
          </button>
          <span v-if="!statusButtons.length" class="muted">Ticket is closed (terminal state).</span>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.layout { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; align-items: start; }
.ticket-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ticket-head h1 { flex: 1 1 auto; font-size: 19px; }
.badge.category { background: var(--accent-soft); color: var(--accent); }
.description { background: #f8fafc; border-radius: 8px; padding: 12px; }
.timeline { display: flex; flex-direction: column; gap: 10px; margin-top: 8px; }
.comment { border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; }
.comment.internal { border-color: #f0c674; background: #fffbeb; }
.comment .meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.comment p { margin: 0; }
.reply { margin-top: 16px; }
.reply .row { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.internal-toggle { font-size: 12px; color: var(--muted); display: flex; gap: 6px; align-items: center; }
.internal-toggle input { width: auto; }
.side { display: flex; flex-direction: column; gap: 16px; }
.triage-grid { display: grid; grid-template-columns: auto 1fr; gap: 4px 16px; margin-top: 8px; }
.suggested { background: #f8fafc; padding: 10px; border-radius: 8px; font-size: 13px; }
.actions { display: flex; flex-direction: column; gap: 8px; }
</style>
