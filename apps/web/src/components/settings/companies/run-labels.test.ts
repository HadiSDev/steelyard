import { describe, expect, it } from 'vitest'
import type { PipelineRunRead } from '#/lib/api/types'
import { inFlightKinds, summaryCounts } from './run-labels'

describe('summaryCounts', () => {
  it('lists the non-zero counts in order', () => {
    expect(summaryCounts({ processed: 3, failed: 0, categorized: 7 })).toEqual([
      '3 processed',
      '7 categorized',
    ])
  })

  it('sums nested per-integration counts by key and skips non-numbers', () => {
    expect(
      summaryCounts({
        status: 'ok',
        integrations: [
          { documents_queued: 2, categorization: { categorized: 4 } },
          { documents_queued: 1, categorization: { categorized: 1 } },
        ],
      }),
    ).toEqual(['3 documents queued', '5 categorized'])
  })

  it('keeps acronyms and shows at most three counts', () => {
    expect(summaryCounts({ ai_failed: 1, a: 1, b: 1, c: 1 })).toEqual([
      '1 AI failed',
      '1 a',
      '1 b',
    ])
  })

  it('is empty without a summary', () => {
    expect(summaryCounts(null)).toEqual([])
  })
})

describe('inFlightKinds', () => {
  it('maps each kind with a queued or running run to its status', () => {
    const base = {
      company_id: 'c1',
      requested_by: 'system',
      requested_at: '2026-09-26T10:00:00Z',
      started_at: null,
      finished_at: null,
      summary: null,
      error: null,
    }
    const runs: Array<PipelineRunRead> = [
      { ...base, id: 'r3', kind: 'categorize', status: 'queued' },
      { ...base, id: 'r2', kind: 'sync', status: 'succeeded' },
      { ...base, id: 'r1', kind: 'read_documents', status: 'running' },
    ]

    expect(Object.fromEntries(inFlightKinds(runs))).toEqual({
      categorize: 'queued',
      read_documents: 'running',
    })
  })
})
