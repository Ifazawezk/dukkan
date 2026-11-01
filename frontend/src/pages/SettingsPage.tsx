import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/client";
import type { Branch, Role, ShopSettings, User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useShop } from "../auth/ShopContext";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  ErrorText,
  Input,
  Modal,
  PageHeader,
  Select,
  td,
  th,
} from "../components/ui";
import { useI18n } from "../i18n";
import { formatDateTime } from "../lib/format";

export function SettingsPage() {
  const { t } = useI18n();
  const { hasRole } = useAuth();
  return (
    <div className="space-y-5">
      <PageHeader title={t("settings.title")} />
      {hasRole("owner", "manager") && <ShopSettingsCard />}
      {hasRole("owner", "manager") && <BranchesCard />}
      {hasRole("owner", "manager") && <UsersCard />}
      <PasswordCard />
    </div>
  );
}

function ShopSettingsCard() {
  const { t } = useI18n();
  const { hasRole } = useAuth();
  const { settings } = useShop();
  const queryClient = useQueryClient();
  const isOwner = hasRole("owner");
  const [form, setForm] = useState<ShopSettings | undefined>(settings);
  const [saved, setSaved] = useState(false);

  useEffect(() => setForm(settings), [settings]);

  const save = useMutation({
    mutationFn: (body: Partial<ShopSettings>) =>
      api<ShopSettings>("/settings", { method: "PATCH", body }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["settings"], updated);
      setSaved(true);
    },
  });

  if (!form) return null;
  const set = <K extends keyof ShopSettings>(key: K, value: ShopSettings[K]) => {
    setSaved(false);
    setForm({ ...form, [key]: value });
  };

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!form) return;
    const { currency: _currency, ...body } = form;
    save.mutate(body);
  }

  return (
    <Card title={t("settings.shop")}>
      <form onSubmit={submit} className="grid gap-4 p-4 sm:grid-cols-2">
        {!isOwner && (
          <p className="text-sm text-stone-500 sm:col-span-2">{t("settings.ownerOnly")}</p>
        )}
        <fieldset disabled={!isOwner} className="contents">
          <Input
            label={t("settings.shopName")}
            value={form.shop_name}
            onChange={(e) => set("shop_name", e.target.value)}
            required
          />
          <Input
            label={t("settings.shopNameAr")}
            dir="rtl"
            value={form.shop_name_ar}
            onChange={(e) => set("shop_name_ar", e.target.value)}
          />
          <Input
            label={t("settings.timezone")}
            value={form.timezone}
            onChange={(e) => set("timezone", e.target.value)}
          />
          <Input
            label={t("settings.taxRate")}
            type="number"
            min="0"
            max="100"
            step="0.01"
            value={form.default_tax_rate}
            onChange={(e) => set("default_tax_rate", Number(e.target.value))}
            hint={t("settings.taxHint")}
          />
          <Input
            label={t("settings.cashierDiscount")}
            type="number"
            min="0"
            max="100"
            step="0.01"
            value={form.max_cashier_discount_percent}
            onChange={(e) => set("max_cashier_discount_percent", Number(e.target.value))}
          />
          <Input
            label={t("settings.lowStock")}
            type="number"
            min="0"
            value={form.default_low_stock_threshold}
            onChange={(e) => set("default_low_stock_threshold", Number(e.target.value))}
          />
          <Input
            label={t("settings.footer")}
            value={form.receipt_footer}
            onChange={(e) => set("receipt_footer", e.target.value)}
          />
          <Input
            label={t("settings.footerAr")}
            dir="rtl"
            value={form.receipt_footer_ar}
            onChange={(e) => set("receipt_footer_ar", e.target.value)}
          />
          <div className="sm:col-span-2">
            <Checkbox
              label={t("settings.negativeStock")}
              checked={form.allow_negative_stock}
              onChange={(value) => set("allow_negative_stock", value)}
            />
          </div>
        </fieldset>
        {isOwner && (
          <div className="flex items-center gap-3 sm:col-span-2">
            <Button type="submit" disabled={save.isPending}>
              {t("common.save")}
            </Button>
            {saved && <span className="text-sm text-emerald-700">{t("settings.saved")}</span>}
            <ErrorText error={save.error} />
          </div>
        )}
      </form>
    </Card>
  );
}

function BranchesCard() {
  const { t } = useI18n();
  const { hasRole } = useAuth();
  const queryClient = useQueryClient();
  const isOwner = hasRole("owner");
  const branches = useQuery({ queryKey: ["branches"], queryFn: () => api<Branch[]>("/branches") });
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", name_ar: "", address: "", phone: "" });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["branches"] });
  const create = useMutation({
    mutationFn: () =>
      api<Branch>("/branches", { body: { ...form, code: form.code.toUpperCase() } }),
    onSuccess: () => {
      setAdding(false);
      setForm({ code: "", name: "", name_ar: "", address: "", phone: "" });
      refresh();
    },
  });
  const toggle = useMutation({
    mutationFn: (branch: Branch) =>
      api<Branch>(`/branches/${branch.id}`, {
        method: "PATCH",
        body: { is_active: !branch.is_active },
      }),
    onSuccess: refresh,
  });

  return (
    <Card
      title={t("settings.branches")}
      actions={
        isOwner && (
          <Button size="sm" icon={<Plus className="size-4" />} onClick={() => setAdding(true)}>
            {t("settings.addBranch")}
          </Button>
        )
      }
    >
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-stone-100">
          <thead className="bg-stone-50">
            <tr>
              <th className={th}>{t("settings.code")}</th>
              <th className={th}>{t("categories.name")}</th>
              <th className={th}>{t("settings.address")}</th>
              <th className={th}>{t("suppliers.phone")}</th>
              <th className={th}>{t("products.status")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {branches.data?.map((b) => (
              <tr key={b.id}>
                <td className={`${td} font-mono`}>{b.code}</td>
                <td className={td}>
                  {b.name}
                  {b.name_ar && <span className="ms-2 text-stone-500">{b.name_ar}</span>}
                </td>
                <td className={td}>{b.address}</td>
                <td className={td} dir="ltr">
                  {b.phone}
                </td>
                <td className={td}>
                  <button disabled={!isOwner} onClick={() => toggle.mutate(b)}>
                    <Badge tone={b.is_active ? "green" : "gray"}>
                      {b.is_active ? t("common.active") : t("common.inactive")}
                    </Badge>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal
        open={adding}
        title={t("settings.addBranch")}
        onClose={() => setAdding(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setAdding(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" form="branch-form" disabled={create.isPending}>
              {t("common.save")}
            </Button>
          </>
        }
      >
        <form
          id="branch-form"
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <Input
            label={t("settings.code")}
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
            placeholder="DOH"
            required
          />
          <Input
            label={t("categories.name")}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <Input
            label={t("categories.nameAr")}
            dir="rtl"
            value={form.name_ar}
            onChange={(e) => setForm({ ...form, name_ar: e.target.value })}
          />
          <Input
            label={t("suppliers.phone")}
            dir="ltr"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
          <Input
            className="sm:col-span-2"
            label={t("settings.address")}
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
          <div className="sm:col-span-2">
            <ErrorText error={create.error} />
          </div>
        </form>
      </Modal>
    </Card>
  );
}

function UsersCard() {
  const { t, lang, pick } = useI18n();
  const { hasRole } = useAuth();
  const { branches, settings } = useShop();
  const isOwner = hasRole("owner");
  const users = useQuery({ queryKey: ["users"], queryFn: () => api<User[]>("/users") });
  const [editing, setEditing] = useState<User | "new" | null>(null);
  const branchName = (id: number | null) => {
    const branch = branches.find((b) => b.id === id);
    return branch ? pick(branch.name, branch.name_ar) : "";
  };

  return (
    <Card
      title={t("settings.users")}
      actions={
        isOwner && (
          <Button size="sm" icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
            {t("settings.addUser")}
          </Button>
        )
      }
    >
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-stone-100">
          <thead className="bg-stone-50">
            <tr>
              <th className={th}>{t("settings.fullName")}</th>
              <th className={th}>{t("login.username")}</th>
              <th className={th}>{t("settings.role")}</th>
              <th className={th}>{t("nav.branch")}</th>
              <th className={th}>{t("settings.lastLogin")}</th>
              <th className={th}>{t("products.status")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {users.data?.map((u) => (
              <tr
                key={u.id}
                className={isOwner ? "cursor-pointer hover:bg-stone-50" : undefined}
                onClick={() => isOwner && setEditing(u)}
              >
                <td className={`${td} font-medium`}>{u.full_name}</td>
                <td className={`${td} font-mono text-stone-600`}>{u.username}</td>
                <td className={td}>
                  <Badge
                    tone={u.role === "owner" ? "brand" : u.role === "manager" ? "blue" : "gray"}
                  >
                    {t(`role.${u.role}`)}
                  </Badge>
                </td>
                <td className={td}>{branchName(u.branch_id)}</td>
                <td className={`${td} text-stone-600`}>
                  {u.last_login_at ? formatDateTime(u.last_login_at, lang, settings?.timezone) : ""}
                </td>
                <td className={td}>
                  <Badge tone={u.is_active ? "green" : "gray"}>
                    {u.is_active ? t("common.active") : t("common.inactive")}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && (
        <UserDialog user={editing === "new" ? null : editing} onClose={() => setEditing(null)} />
      )}
    </Card>
  );
}

function UserDialog({ user, onClose }: { user: User | null; onClose: () => void }) {
  const { t, pick } = useI18n();
  const { branches } = useShop();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    username: user?.username ?? "",
    full_name: user?.full_name ?? "",
    role: user?.role ?? ("cashier" as Role),
    branch_id: user?.branch_id ? String(user.branch_id) : String(branches[0]?.id ?? ""),
    password: "",
    is_active: user?.is_active ?? true,
  });

  const save = useMutation({
    mutationFn: () => {
      const branch_id = form.branch_id ? Number(form.branch_id) : null;
      if (user) {
        return api<User>(`/users/${user.id}`, {
          method: "PATCH",
          body: {
            full_name: form.full_name,
            role: form.role,
            branch_id,
            is_active: form.is_active,
            ...(form.password ? { password: form.password } : {}),
          },
        });
      }
      return api<User>("/users", {
        body: {
          username: form.username,
          full_name: form.full_name,
          role: form.role,
          branch_id,
          password: form.password,
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
  });

  return (
    <Modal
      open
      title={user ? t("settings.editUser") : t("settings.addUser")}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form="user-form" disabled={save.isPending}>
            {t("common.save")}
          </Button>
        </>
      }
    >
      <form
        id="user-form"
        className="grid gap-4 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Input
          label={t("settings.fullName")}
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          required
        />
        <Input
          label={t("login.username")}
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
          disabled={!!user}
          required
        />
        <Select
          label={t("settings.role")}
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
        >
          {(["cashier", "manager", "owner"] as const).map((role) => (
            <option key={role} value={role}>
              {t(`role.${role}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t("nav.branch")}
          value={form.branch_id}
          onChange={(e) => setForm({ ...form, branch_id: e.target.value })}
        >
          <option value="">{t("common.none")}</option>
          {branches.map((b) => (
            <option key={b.id} value={b.id}>
              {pick(b.name, b.name_ar)}
            </option>
          ))}
        </Select>
        <Input
          className="sm:col-span-2"
          label={t("settings.newPassword")}
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          hint={user ? t("settings.passwordHint") : undefined}
          required={!user}
          minLength={8}
        />
        {user && (
          <Checkbox
            label={t("common.active")}
            checked={form.is_active}
            onChange={(value) => setForm({ ...form, is_active: value })}
          />
        )}
        <div className="sm:col-span-2">
          <ErrorText error={save.error} />
        </div>
      </form>
    </Modal>
  );
}

function PasswordCard() {
  const { t } = useI18n();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [done, setDone] = useState(false);
  const change = useMutation({
    mutationFn: () =>
      api<void>("/auth/change-password", {
        body: { current_password: current, new_password: next },
      }),
    onSuccess: () => {
      setCurrent("");
      setNext("");
      setDone(true);
    },
  });

  return (
    <Card title={t("settings.myPassword")}>
      <form
        className="flex flex-wrap items-end gap-3 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          setDone(false);
          change.mutate();
        }}
      >
        <Input
          label={t("settings.currentPassword")}
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          required
        />
        <Input
          label={t("settings.newPassword")}
          type="password"
          autoComplete="new-password"
          minLength={8}
          value={next}
          onChange={(e) => setNext(e.target.value)}
          required
        />
        <Button type="submit" disabled={change.isPending}>
          {t("common.save")}
        </Button>
        {done && (
          <span className="pb-2 text-sm text-emerald-700">{t("settings.passwordChanged")}</span>
        )}
        <ErrorText error={change.error} />
      </form>
    </Card>
  );
}
