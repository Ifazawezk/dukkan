import { Languages, Store } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, ErrorText, Input } from "../components/ui";
import { useI18n } from "../i18n";
import { homeFor } from "../routes";

export function LoginPage() {
  const { user, login } = useAuth();
  const { t, lang, setLang } = useI18n();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const signedIn = await login(username, password);
      navigate(homeFor(signedIn.role), { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401 ? t("login.failed") : t("common.error"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-brand-900 via-brand-800 to-stone-900 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-between text-white">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-xl bg-white/10 ring-1 ring-white/20">
              <Store className="size-5" />
            </span>
            <div>
              <div className="text-lg font-semibold">{t("app.name")}</div>
              <div className="text-sm text-brand-100">{t("app.tagline")}</div>
            </div>
          </div>
          <button
            onClick={() => setLang(lang === "en" ? "ar" : "en")}
            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm text-brand-100 hover:bg-white/10"
          >
            <Languages className="size-4" />
            {t("nav.language")}
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4 rounded-2xl bg-white p-6 shadow-xl">
          <h1 className="text-lg font-semibold">{t("login.title")}</h1>
          <Input
            label={t("login.username")}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
          <Input
            label={t("login.password")}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {error && <ErrorText error={error} />}
          <Button type="submit" className="w-full" size="lg" disabled={busy}>
            {t("login.submit")}
          </Button>
          <p className="text-center text-xs text-stone-500">{t("login.demo")}</p>
        </form>
      </div>
    </div>
  );
}
