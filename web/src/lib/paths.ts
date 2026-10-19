/** Strip trailing slashes so "/boats/" and "/boats" compare equal; "" → "/". */
export function normalizePath(path: string): string {
  const trimmed = path.replace(/\/+$/, "");
  return trimmed === "" ? "/" : trimmed;
}

