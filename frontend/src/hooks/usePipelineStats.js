import { useQuery } from "@tanstack/react-query";
import { fetchPipelineStats } from "../lib/pipeline";

export function usePipelineStats() {
  return useQuery({
    queryKey: ["pipelineStats"],
    queryFn: fetchPipelineStats,
  });
}
