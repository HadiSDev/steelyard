import { describe, expect, it, vi } from 'vitest'
import { QueryClient } from '@tanstack/react-query'
import {
  RUN_POLL_INTERVAL_MS,
  companyRunsQueryOptions,
  isRunInFlight,
  requestRunMutation,
  runsRefetchInterval,
} from './pipeline-runs'
import type { ApiClient } from './api-client'
import type { PipelineRunRead, PipelineRunStatus } from './types'

function run(status: PipelineRunStatus, id = 'r1'): PipelineRunRead {
  return {
    id,
    company_id: 'c1',
    kind: 'categorize',
    status,
    requested_by: 'user_1',
    requested_at: '2026-09-26T10:00:00Z',
    started_at: null,
    finished_at: null,
    summary: null,
    error: null,
  }
}

describe('companyRunsQueryOptions', () => {
  it('fetches the company runs with a limit', async () => {
    const get = vi.fn().mockResolvedValue([])
    const api = { get } as unknown as ApiClient

    const options = companyRunsQueryOptions(api, 'c1')
    await options.queryFn!({} as never)

    expect(get).toHaveBeenCalledWith('/api/v1/companies/c1/runs', {
      limit: 20,
    })
    expect(options.queryKey).toEqual(['pipeline-runs', 'c1'])
  })
})

describe('runsRefetchInterval', () => {
  it('polls while the newest run is queued', () => {
    expect(runsRefetchInterval([run('queued')])).toBe(RUN_POLL_INTERVAL_MS)
  })

  it('polls while the newest run is running', () => {
    expect(runsRefetchInterval([run('running'), run('failed', 'r0')])).toBe(
      3000,
    )
  })

  it('keeps polling while an older run is still in flight', () => {
    expect(runsRefetchInterval([run('succeeded'), run('running', 'r0')])).toBe(
      RUN_POLL_INTERVAL_MS,
    )
  })

  it('stops once every run has finished', () => {
    expect(runsRefetchInterval([run('succeeded'), run('failed', 'r0')])).toBe(
      false,
    )
  })

  it('does not poll with no runs or no data', () => {
    expect(runsRefetchInterval([])).toBe(false)
    expect(runsRefetchInterval(undefined)).toBe(false)
  })
})

describe('isRunInFlight', () => {
  it('is true only for queued and running runs', () => {
    expect(isRunInFlight(run('queued'))).toBe(true)
    expect(isRunInFlight(run('running'))).toBe(true)
    expect(isRunInFlight(run('succeeded'))).toBe(false)
    expect(isRunInFlight(undefined)).toBe(false)
  })
})

describe('requestRunMutation', () => {
  it('posts the kind to the company runs path', async () => {
    const post = vi.fn().mockResolvedValue(run('queued'))
    const api = { post } as unknown as ApiClient

    const options = requestRunMutation(api, new QueryClient())
    await options.mutationFn!(
      { companyId: 'c1', kind: 'read_documents' },
      {} as never,
    )

    expect(post).toHaveBeenCalledWith('/api/v1/companies/c1/runs', {
      kind: 'read_documents',
    })
  })

  it('refreshes that company runs on success', async () => {
    const queryClient = new QueryClient()
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    const options = requestRunMutation({} as ApiClient, queryClient)

    await options.onSuccess!(
      run('queued'),
      { companyId: 'c1', kind: 'categorize' },
      undefined,
      {} as never,
    )

    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ['pipeline-runs', 'c1'],
    })
  })
})
