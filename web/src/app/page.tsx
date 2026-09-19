import { Dashboard } from "@/components/Dashboard";
import { loadDashboardData } from "@/lib/dashboard-data";

export default async function Home() {
  const data = await loadDashboardData();
  return (
    <div className="min-h-screen bg-[#f9f9f7]">
      <Dashboard data={data} />
    </div>
  );
}
