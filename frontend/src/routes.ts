import type { Role } from "./api/types";

/** Where each role lands after signing in. */
export function homeFor(role: Role): string {
  return role === "cashier" ? "/pos" : "/products";
}
