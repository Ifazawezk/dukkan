import {
  BarChart3,
  Boxes,
  Languages,
  LogOut,
  Package,
  ReceiptText,
  Settings,
  ShoppingCart,
  Store,
  Truck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import type { Role } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useShop } from "../auth/ShopContext";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import { cx } from "./ui";

interface NavItem {
  to: string;
  label: MessageKey;
  icon: LucideIcon;
  roles: Role[];
}

const ALL: Role[] = ["owner", "manager", "cashier"];
const MANAGERS: Role[] = ["owner", "manager"];

export const NAV: NavItem[] = [
  { to: "/pos", label: "nav.pos", icon: ShoppingCart, roles: ALL },
  { to: "/sales", label: "nav.sales", icon: ReceiptText, roles: ALL },
  { to: "/products", label: "nav.products", icon: Package, roles: ALL },
  { to: "/inventory", label: "nav.inventory", icon: Boxes, roles: ALL },
  { to: "/purchasing", label: "nav.purchasing", icon: Truck, roles: MANAGERS },
  { to: "/reports", label: "nav.reports", icon: BarChart3, roles: MANAGERS },
  { to: "/settings", label: "nav.settings", icon: Settings, roles: ALL },
];

export function Layout() {
  const { user, logout } = useAuth();
  const { settings, branches, branchId, setBranchId, canSwitchBranch } = useShop();
  const { t, lang, setLang, pick } = useI18n();
  if (!user) return null;

  const items = NAV.filter((item) => item.roles.includes(user.role));
  const shopName = settings ? pick(settings.shop_name, settings.shop_name_ar) : t("app.name");

  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col bg-stone-900 text-stone-300 md:min-h-screen md:w-56">
        <div className="flex items-center gap-2 px-4 py-4 text-white">
          <span className="grid size-8 place-items-center rounded-lg bg-brand-700">
            <Store className="size-4" />
          </span>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">{shopName}</div>
            <div className="text-xs text-stone-400">{t("app.name")}</div>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-0">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cx(
                  "flex shrink-0 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                  isActive ? "bg-brand-700 text-white" : "hover:bg-stone-800 hover:text-white",
                )
              }
            >
              <Icon className="size-4" />
              {t(label)}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto hidden border-t border-stone-800 p-4 text-xs md:block">
          <div className="font-medium text-stone-200">{user.full_name}</div>
          <div className="text-stone-400">{t(`role.${user.role}`)}</div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-end gap-2 border-b border-stone-200 bg-white px-4 py-2">
          {branches.length > 0 && (
            <label className="flex items-center gap-2 text-sm text-stone-600">
              {t("nav.branch")}
              <select
                className="h-9 rounded-lg border border-stone-300 bg-white px-2 text-sm disabled:bg-stone-50"
                value={branchId ?? ""}
                disabled={!canSwitchBranch}
                onChange={(e) => setBranchId(Number(e.target.value))}
              >
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {pick(b.name, b.name_ar)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button
            onClick={() => setLang(lang === "en" ? "ar" : "en")}
            className="inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm text-stone-700 hover:bg-stone-100"
          >
            <Languages className="size-4" />
            {t("nav.language")}
          </button>
          <button
            onClick={logout}
            className="inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm text-stone-700 hover:bg-stone-100"
          >
            <LogOut className="size-4 rtl:-scale-x-100" />
            {t("nav.logout")}
          </button>
        </header>
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
