import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores/auth";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/tickets" },
    { path: "/login", component: () => import("./views/LoginView.vue") },
    { path: "/tickets", component: () => import("./views/TicketsView.vue") },
    { path: "/tickets/:id", component: () => import("./views/TicketDetailView.vue") },
    { path: "/dashboard", component: () => import("./views/DashboardView.vue") },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.path !== "/login" && !auth.isLoggedIn) return "/login";
  if (to.path === "/login" && auth.isLoggedIn) return "/tickets";
});
