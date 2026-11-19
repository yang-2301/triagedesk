import { defineStore } from "pinia";
import { api, loadAuth, saveAuth, type AuthData } from "../api";

export const useAuthStore = defineStore("auth", {
  state: () => ({ auth: loadAuth() as AuthData | null }),
  getters: {
    isLoggedIn: (s) => !!s.auth,
    role: (s) => s.auth?.user.role ?? null,
    isStaff: (s) => s.auth?.user.role === "agent" || s.auth?.user.role === "admin",
    name: (s) => s.auth?.user.name ?? "",
  },
  actions: {
    async login(email: string, password: string) {
      this.auth = await api.post<AuthData>("/api/auth/login", { email, password });
      saveAuth(this.auth);
    },
    async register(email: string, password: string, name: string) {
      this.auth = await api.post<AuthData>("/api/auth/register", { email, password, name, role: "customer" });
      saveAuth(this.auth);
    },
    logout() {
      this.auth = null;
      saveAuth(null);
    },
  },
});
