<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();

const mode = ref<"login" | "register">("login");
const email = ref("");
const password = ref("");
const name = ref("");
const busy = ref(false);
const error = ref("");

const DEMOS = [
  { label: "Agent", email: "agent@demo.dev", password: "agent-demo-1234" },
  { label: "Admin", email: "admin@demo.dev", password: "admin-demo-1234" },
  { label: "Customer", email: "customer1@demo.dev", password: "customer-demo-1234" },
];

function useDemo(d: { email: string; password: string }) {
  email.value = d.email;
  password.value = d.password;
  mode.value = "login";
}

async function submit() {
  error.value = "";
  busy.value = true;
  try {
    if (mode.value === "login") await auth.login(email.value, password.value);
    else await auth.register(email.value, password.value, name.value || email.value);
    router.push(auth.isStaff ? "/dashboard" : "/tickets");
  } catch (e: any) {
    error.value = e.message ?? "Something went wrong";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="wrap">
    <div class="hero">
      <h1>Triage<span class="accent">Desk</span></h1>
      <p class="muted">
        Every ticket is auto-triaged on arrival — category, priority and a draft reply
        — before a human ever sees it.
      </p>
    </div>

    <form class="card form" @submit.prevent="submit">
      <h2>{{ mode === "login" ? "Sign in" : "Create account" }}</h2>

      <label v-if="mode === 'register'">Name
        <input v-model="name" placeholder="Jane Doe" />
      </label>
      <label>Email
        <input v-model="email" type="email" required placeholder="you@company.com" />
      </label>
      <label>Password
        <input v-model="password" type="password" required minlength="8" placeholder="••••••••" />
      </label>

      <p v-if="error" class="error-text">{{ error }}</p>

      <button class="primary" type="submit" :disabled="busy">
        {{ busy ? "Working…" : mode === "login" ? "Sign in" : "Sign up" }}
      </button>

      <p class="muted">
        {{ mode === "login" ? "No account?" : "Already registered?" }}
        <a href="#" @click.prevent="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === "login" ? "Sign up" : "Sign in" }}
        </a>
      </p>

      <div class="demos">
        <span class="muted">Demo accounts:</span>
        <button v-for="d in DEMOS" :key="d.email" type="button" @click="useDemo(d)">
          {{ d.label }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.wrap { max-width: 420px; margin: 48px auto; }
.hero { text-align: center; margin-bottom: 24px; }
.hero h1 { font-size: 30px; }
.accent { color: var(--accent); }
.form { display: flex; flex-direction: column; gap: 12px; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); }
.demos { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
</style>
