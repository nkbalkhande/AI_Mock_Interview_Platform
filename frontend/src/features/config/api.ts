import { apiClient } from "@/lib/api-client";

import type { PublicConfig } from "./types";

/** GET /config/public — non-secret interview limits from settings/config.yaml. */
export async function getPublicConfig(): Promise<PublicConfig> {
  const { data } = await apiClient.get<PublicConfig>("/config/public");
  return data;
}
