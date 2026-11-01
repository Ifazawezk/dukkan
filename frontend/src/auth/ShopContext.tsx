import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import type { Branch, ShopSettings } from "../api/types";
import { useAuth } from "./AuthContext";

interface Shop {
  settings: ShopSettings | undefined;
  branches: Branch[];
  branchId: number | null;
  branch: Branch | undefined;
  setBranchId: (id: number) => void;
  canSwitchBranch: boolean;
}

const ShopContext = createContext<Shop | null>(null);
const BRANCH_KEY = "dukkan.branch";

export function ShopProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: () => api<ShopSettings>("/settings"),
    enabled: !!user,
  });
  const branches = useQuery({
    queryKey: ["branches"],
    queryFn: () => api<Branch[]>("/branches"),
    enabled: !!user,
  });

  const [chosen, setChosen] = useState<number | null>(() => {
    const saved = Number(localStorage.getItem(BRANCH_KEY));
    return Number.isFinite(saved) && saved > 0 ? saved : null;
  });

  const active = useMemo(() => (branches.data ?? []).filter((b) => b.is_active), [branches.data]);
  const canSwitchBranch = !!user && user.role !== "cashier";

  // Cashiers always work in their own branch; others pick one, defaulting to home.
  let branchId: number | null = null;
  if (user) {
    if (!canSwitchBranch) branchId = user.branch_id;
    else if (chosen && active.some((b) => b.id === chosen)) branchId = chosen;
    else branchId = user.branch_id ?? active[0]?.id ?? null;
  }

  useEffect(() => {
    if (branchId && canSwitchBranch) localStorage.setItem(BRANCH_KEY, String(branchId));
  }, [branchId, canSwitchBranch]);

  const value = useMemo<Shop>(
    () => ({
      settings: settings.data,
      branches: active,
      branchId,
      branch: active.find((b) => b.id === branchId),
      setBranchId: setChosen,
      canSwitchBranch,
    }),
    [settings.data, active, branchId, canSwitchBranch],
  );

  return <ShopContext.Provider value={value}>{children}</ShopContext.Provider>;
}

export function useShop(): Shop {
  const value = useContext(ShopContext);
  if (!value) throw new Error("useShop must be used inside ShopProvider");
  return value;
}
