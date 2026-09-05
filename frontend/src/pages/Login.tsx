import { useState } from "react";
import { Leaf, ShieldCheck, Boxes, Sparkles, LogIn } from "lucide-react";
import { useAuth } from "../auth";

const REMEMBER_KEY = "skac_remember_login";

function loadRemembered() {
  try {
    const raw = localStorage.getItem(REMEMBER_KEY);
    if (!raw) return { email: "", password: "", remember: false };
    const parsed = JSON.parse(raw);
    return {
      email: String(parsed.email || ""),
      password: String(parsed.password || ""),
      remember: true,
    };
  } catch {
    return { email: "", password: "", remember: false };
  }
}

export default function Login() {
  const { login } = useAuth();
  const saved = loadRemembered();
  const [email, setEmail] = useState(saved.email);
  const [password, setPassword] = useState(saved.password);
  const [remember, setRemember] = useState(saved.remember);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const em = email.trim();
    const pw = password;
    if (!em && !pw) { setError("Please enter your email and password."); return; }
    if (!em) { setError("Please enter your email address."); return; }
    if (!em.includes("@") || !em.includes(".")) { setError("Please enter a valid email address."); return; }
    if (!pw) { setError("Please enter your password."); return; }
    setError(""); setBusy(true);
    try {
      await login(em, pw);
      if (remember) localStorage.setItem(REMEMBER_KEY, JSON.stringify({ email: em, password: pw }));
      else localStorage.removeItem(REMEMBER_KEY);
    } catch (err: any) {
      setError(err.message || "Sign in failed. Check your email and password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <div className="brand" style={{ padding: 0, marginBottom: 8 }}>
          <div className="brand-logo"><Leaf size={22} /></div>
          <div className="brand-name" style={{ fontSize: 22 }}>SKAC</div>
        </div>
        <h1>Sri Kumaran<br />Agri Clinic</h1>
        <p>Enterprise cloud billing & inventory for fertilizer, pesticide and seed retail — multi-branch, GST-compliant, and AI-assisted.</p>
        <div className="auth-features">
          <div className="auth-feature"><span className="fi"><Boxes size={18} /></span> Batch & expiry-aware inventory across every branch</div>
          <div className="auth-feature"><span className="fi"><ShieldCheck size={18} /></span> GST invoicing, licenses & statutory compliance</div>
          <div className="auth-feature"><span className="fi"><Sparkles size={18} /></span> AI demand forecasting & natural-language reports</div>
        </div>
      </div>

      <div className="auth-form-col">
        <form className="auth-card" onSubmit={submit} noValidate>
          <h2>Welcome back</h2>
          <p className="muted" style={{ margin: "6px 0 22px" }}>Sign in to your account</p>
          <div className="field">
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </div>
          <label className="row" style={{ gap: 8, cursor: "pointer", marginBottom: 14 }}>
            <input type="checkbox" style={{ width: "auto" }} checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Remember username and password
          </label>
          {error && <div className="error">{error}</div>}
          <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
            <LogIn size={18} /> {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
