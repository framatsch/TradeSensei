"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createTokenApiV1SettingsTokensPost,
  listTokensApiV1SettingsTokensGet,
  revokeTokenApiV1SettingsTokensTokenIdDelete,
  type PatGenerateRequest,
  type PatGenerateResponse,
  type PatRead,
} from "@/lib/api";

export const API_TOKENS_QUERY_KEY = ["settings", "api-tokens"] as const;

export function useApiTokens() {
  return useQuery<PatRead[], Error>({
    queryKey: API_TOKENS_QUERY_KEY,
    queryFn: async () => {
      const { data, error } = await listTokensApiV1SettingsTokensGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 30_000,
  });
}

export function useCreateApiToken() {
  const qc = useQueryClient();

  return useMutation<PatGenerateResponse, Error, PatGenerateRequest>({
    mutationFn: async (payload) => {
      const { data, error } = await createTokenApiV1SettingsTokensPost({
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: API_TOKENS_QUERY_KEY });
    },
  });
}

export function useRevokeApiToken() {
  const qc = useQueryClient();

  return useMutation<void, Error, string, { previous?: PatRead[] }>({
    mutationFn: async (tokenId) => {
      const { error } = await revokeTokenApiV1SettingsTokensTokenIdDelete({
        path: { token_id: tokenId },
      });
      if (error) throw error;
    },
    onMutate: async (tokenId) => {
      await qc.cancelQueries({ queryKey: API_TOKENS_QUERY_KEY });
      const previous = qc.getQueryData<PatRead[]>(API_TOKENS_QUERY_KEY);
      qc.setQueryData<PatRead[]>(API_TOKENS_QUERY_KEY, (current) => {
        if (!current) return current;
        return current.map((token) =>
          token.id === tokenId ? { ...token, is_revoked: true } : token
        );
      });
      return { previous };
    },
    onError: (_error, _tokenId, context) => {
      if (context?.previous) {
        qc.setQueryData(API_TOKENS_QUERY_KEY, context.previous);
      }
    },
    onSettled: async () => {
      await qc.invalidateQueries({ queryKey: API_TOKENS_QUERY_KEY });
    },
  });
}
