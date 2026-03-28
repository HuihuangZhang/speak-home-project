"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function AuthPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const fn = tab === "login" ? api.auth.login : api.auth.register;
      const res = await fn(email, password);
      localStorage.setItem("access_token", res.access_token);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
      <div style={{ background: "#fff", padding: 32, borderRadius: 12, width: 360, boxShadow: "0 2px 12px #0001" }}>
        <h1 style={{ textAlign: "center", marginBottom: 24 }}>Speak Home</h1>

        {/* Tabs */}
        <div style={{ display: "flex", marginBottom: 24, borderBottom: "1px solid #e0e0e0" }}>
          {(["login", "register"] as const).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => { setTab(t); setError(""); }}
              style={{
                flex: 1, padding: "10px 0", background: "none", border: "none",
                cursor: "pointer", fontWeight: tab === t ? 700 : 400,
                borderBottom: tab === t ? "2px solid #6366f1" : "none",
                textTransform: "capitalize",
              }}
            >
              {t === "login" ? "Login" : "Register"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit}>
          <label htmlFor="email" style={{ display: "block", marginBottom: 4, fontSize: 14 }}>Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid #ccc", marginBottom: 16, boxSizing: "border-box" }}
          />

          <label htmlFor="password" style={{ display: "block", marginBottom: 4, fontSize: 14 }}>Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid #ccc", marginBottom: 24, boxSizing: "border-box" }}
          />

          {error && (
            <div role="alert" style={{ color: "#dc2626", fontSize: 14, marginBottom: 16, padding: "8px 12px", background: "#fef2f2", borderRadius: 6 }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{ width: "100%", padding: "12px 0", background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, fontSize: 16, cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? "..." : tab === "login" ? "Login" : "Register"}
          </button>
        </form>
      </div>
    </main>
  );
}
