/** Strip trailing slashes so "/boats/" and "/boats" compare equal; "" → "/". */
export function normalizePath(path: string): string {
  const trimmed = path.replace(/\/+$/, "");
  return trimmed === "" ? "/" : trimmed;
}

/**
 * Whether a nav link should be marked current. `pathname` comes from
 * usePathname(), which excludes the basePath, so it compares directly
 * against app-relative hrefs like "/boats/".
 */
export function isActivePath(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  const current = normalizePath(pathname);
  const target = normalizePath(href);
  if (target === "/") return current === "/";
  return current === target || current.startsWith(`${target}/`);
}
