import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router } from "./router";
import { useAuthStore } from "./stores/auth";
import "./style.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);

// Demo hook: /?demo=agent|admin|customer auto-logs in with the seeded demo
// account and follows the ?next= route (used for screenshots & docs).
const params = new URLSearchParams(window.location.search);
const demoRole = params.get("demo");
const nextPath = params.get("next") || "/dashboard";
if (demoRole && !useAuthStore().isLoggedIn) {
  const accounts: Record<string, { email: string; password: string }> = {
    agent: { email: "agent@demo.dev", password: "agent-demo-1234" },
    admin: { email: "admin@demo.dev", password: "admin-demo-1234" },
    customer: { email: "customer1@demo.dev", password: "customer-demo-1234" },
  };
  const account = accounts[demoRole];
  if (account) {
    useAuthStore()
      .login(account.email, account.password)
      .then(() => router.push(nextPath))
      .catch(() => router.push("/login"));
  }
}

app.mount("#app");
