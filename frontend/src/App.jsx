import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Sidebar from "./components/Sidebar";
import MatchesDashboard from "./pages/MatchesDashboard";
import PipelineOverview from "./pages/PipelineOverview";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  const [activeNav, setActiveNav] = useState("pipeline");

  const handleOpenMatch = (match) => {
    // Match Detail page wiring goes here next
    console.log("open match", match.id);
  };

  const renderPage = () => {
    switch (activeNav) {
      case "pipeline":
        return <PipelineOverview />;
      case "dashboard":
        return <MatchesDashboard onOpenMatch={handleOpenMatch} />;
      case "drafts":
      case "profile":
        return (
          <div className="flex-1 flex items-center justify-center text-muted font-body">
            This page is coming soon.
          </div>
        );
      default:
        return <PipelineOverview />;
    }
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-void bg-radial-glow flex">
        <Sidebar active={activeNav} onNavigate={setActiveNav} />
        {renderPage()}
      </div>
    </QueryClientProvider>
  );
}
