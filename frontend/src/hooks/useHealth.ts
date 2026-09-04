import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "@/api/health";

export const useHealth = () =>
  useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 5_000,
  });
