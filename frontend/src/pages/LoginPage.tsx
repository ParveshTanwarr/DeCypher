import { useState } from "react";
import type { FormEvent } from "react";
import { login } from "../api/client";

interface LoginPageProps {
  onLogin: (token: string) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("adminpassword");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const token = await login(username, password);
      onLogin(token);
    } catch {
      setError("Authentication failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="brand-mark">D</div>

        <h1>DeCypher</h1>
        <p className="subtitle">Threat Intelligence & Attribution Platform</p>

        <form onSubmit={handleSubmit}>
          <label>Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />

          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />

          {error && <div className="error">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? "Authenticating..." : "Sign in"}
          </button>
        </form>

        <div className="login-footer">
          Authorized investigation environment
        </div>
      </div>
    </div>
  );
}