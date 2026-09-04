import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { Toaster } from "@/components/ui/Toaster";
import { Dashboard } from "@/pages/Dashboard";
import { OutboundCall } from "@/pages/OutboundCall";
import { Talk } from "@/pages/Talk";
import { FreelancerProfilePage } from "@/pages/FreelancerProfile";
import { Leads } from "@/pages/Leads";

export default function App() {
  return (
    <Toaster>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/outbound" element={<OutboundCall />} />
          <Route path="/talk" element={<Talk />} />
          <Route path="/freelancer/profile" element={<FreelancerProfilePage />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </Toaster>
  );
}
