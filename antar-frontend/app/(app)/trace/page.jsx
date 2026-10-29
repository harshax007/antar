import dynamic from "next/dynamic";
import AccountSidebar from "@/components/AccountSidebar";
import BrainLoader, { TRACE_STEPS, TRACE_ORBS } from "@/components/BrainLoader";

export const metadata = {
  title: "Observability & Trace | Antar",
  description: "AI Observability and Tracing Telemetry",
};

const TrustDashboard = dynamic(() => import("@/components/TrustDashboard"), {
  ssr: false,
  loading: () => (
    <div style={{ position: "relative", minHeight: "100vh", height: "100%", width: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--void, #060910)" }}>
      <BrainLoader steps={TRACE_STEPS} orbs={TRACE_ORBS} />
    </div>
  ),
});

export default function TracePage() {
  return (
    <div className="ac-page">
      <AccountSidebar activeSection="trace" />
      <div className="ac-main" style={{ padding: 0, overflowY: "auto", background: "var(--void, #060910)" }}>
        <TrustDashboard />
      </div>
    </div>
  );
}
