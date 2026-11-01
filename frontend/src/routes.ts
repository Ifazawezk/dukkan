import type { Role } from "./api/types";

/** Where each role lands after signing in. */
export function homeFor(_role: Role): string {
  return "/products";
}
