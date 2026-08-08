import { QueryClient } from "@tanstack/react-query";

/** Factory for a configured QueryClient (one per browser session). */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}
