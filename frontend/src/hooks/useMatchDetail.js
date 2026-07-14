import { useQuery } from "@tanstack/react-query";
import { fetchMatchById } from "../lib/matches";

export function useMatchDetail(id) {
  return useQuery({
    queryKey: ["match", id],
    queryFn: () => fetchMatchById(id),
    enabled: !!id,
  });
}
