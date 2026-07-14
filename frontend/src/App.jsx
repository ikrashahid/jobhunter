import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Sidebar from "./components/Sidebar";
import MatchesDashboard from "./pages/MatchesDashboard";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  const [activeNav, setActiveNav] = useState("dashboard");

  const handleOpenMatch = (match) => {
    // Match Detail page wiring goes here next
    console.log("open match", match.id);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-void bg-radial-glow flex">
        <Sidebar active={activeNav} onNavigate={setActiveNav} />
        <MatchesDashboard onOpenMatch={handleOpenMatch} />
      </div>
    </QueryClientProvider>
  );
}
