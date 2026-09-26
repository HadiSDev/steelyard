import { queryOptions } from '@tanstack/react-query'
import type { QueryClient, UseMutationOptions } from '@tanstack/react-query'
import type { ApiClient } from './api-client'
import type { PipelineRunKind, PipelineRunRead } from './types'

/** How often a company's runs are refetched while one is in flight. */
export const RUN_POLL_INTERVAL_MS = 3000

/** How many recent runs the settings row asks for. */
const RECENT_RUN_LIMIT = 20

/** Key prefix for every company's run list. */
export const pipelineRunsKey = ['pipeline-runs'] as const

/** Whether a run has yet to finish. */
export function isRunInFlight(run: PipelineRunRead | undefined): boolean {
  if (!run) {
    return false
  }
  return run.status === 'queued' || run.status === 'running'
}

/** The poll interval for a run list: only while one of its runs is in flight. */
export function runsRefetchInterval(
  runs: Array<PipelineRunRead> | undefined,
): number | false {
  if (runs?.some(isRunInFlight)) {
    return RUN_POLL_INTERVAL_MS
  }
  return false
}

/** A company's recent pipeline runs, newest first (`GET /companies/{id}/runs`). */
export function companyRunsQueryOptions(api: ApiClient, companyId: string) {
  return queryOptions({
    queryKey: [...pipelineRunsKey, companyId],
    queryFn: () =>
      api.get<Array<PipelineRunRead>>(`/api/v1/companies/${companyId}/runs`, {
        limit: RECENT_RUN_LIMIT,
      }),
    refetchInterval: (query) => runsRefetchInterval(query.state.data),
  })
}

/** Ask the worker to run one pipeline stage for a company (`POST /companies/{id}/runs`). */
export function requestRunMutation(
  api: ApiClient,
  queryClient: QueryClient,
): UseMutationOptions<
  PipelineRunRead,
  Error,
  { companyId: string; kind: PipelineRunKind }
> {
  return {
    mutationFn: ({ companyId, kind }) =>
      api.post<PipelineRunRead>(`/api/v1/companies/${companyId}/runs`, {
        kind,
      }),
    onSuccess: (_run, { companyId }) =>
      queryClient.invalidateQueries({
        queryKey: [...pipelineRunsKey, companyId],
      }),
  }
}
