/** Owner sees every screen and every branch. Cashier is limited to counter work. */

export const ROLE_OWNER = "owner";
export const ROLE_CASHIER = "cashier";

export const CASHIER_PATHS = new Set([
  "/pos",
  "/invoices",
  "/returns",
  "/customers",
  "/expenses",
  "/day-close",
  "/field-visits",
]);

export function isOwner(user: { role?: string } | null | undefined): boolean {
  return user?.role === ROLE_OWNER;
}

export function isCashier(user: { role?: string } | null | undefined): boolean {
  return user?.role === ROLE_CASHIER;
}

export function canAccessPath(user: { role?: string } | null | undefined, path: string): boolean {
  if (!user) return false;
  if (isOwner(user)) return true;
  return CASHIER_PATHS.has(path);
}

export function homePath(user: { role?: string } | null | undefined): string {
  return isCashier(user) ? "/pos" : "/";
}

export function seesAllBranches(user: { role?: string } | null | undefined): boolean {
  return isOwner(user);
}
