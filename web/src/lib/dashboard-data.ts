import { readFile } from "node:fs/promises";
import path from "node:path";
import type { DashboardData } from "./types";

export async function loadDashboardData(): Promise<DashboardData> {
  const filePath = path.join(process.cwd(), "public", "data", "dashboard.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as DashboardData;
}
