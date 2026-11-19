<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const router = useRouter();

function logout() {
  auth.logout();
  router.push("/login");
}
</script>

<template>
  <div v-if="auth.isLoggedIn" class="topnav">
    <div class="brand">Triage<span class="accent">Desk</span></div>
    <nav class="links">
      <router-link to="/tickets">Tickets</router-link>
      <router-link v-if="auth.isStaff" to="/dashboard">Dashboard</router-link>
    </nav>
    <div class="spacer" />
    <span class="muted">{{ auth.name }} · {{ auth.role }}</span>
    <button @click="logout">Sign out</button>
  </div>
  <main>
    <router-view />
  </main>
</template>

<style scoped>
.topnav {
  display: flex; align-items: center; gap: 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 10px 24px;
}
.brand { font-weight: 700; font-size: 17px; }
.brand .accent { color: var(--accent); }
.links { display: flex; gap: 16px; }
.links a { color: var(--muted); text-decoration: none; font-weight: 550; }
.links a.router-link-active { color: var(--accent); }
.spacer { flex: 1; }
main { max-width: 1080px; margin: 24px auto; padding: 0 24px; }
</style>
