import { describe, expect, it, vi } from 'vitest'
import { supplierOverviewQueryOptions } from './vendors'
import type { ApiClient } from './api-client'

function fakeApi() {
  const get = vi
    .fn()
    .mockResolvedValue({ items: [], page: 1, page_size: 25, total: 0 })
  return { api: { get } as unknown as ApiClient, get }
}

describe('supplierOverviewQueryOptions', () => {
  it('asks the overview endpoint with the page’s filters', async () => {
    const { api, get } = fakeApi()
    const filters = {
      q: 'google',
      company_id: 'c1',
      sort: 'spend' as const,
      page: 2,
    }
    const options = supplierOverviewQueryOptions(api, filters)

    await options.queryFn!({} as never)

    expect(get).toHaveBeenCalledWith('/api/v1/vendors/overview', filters)
    expect(options.queryKey).toEqual(['vendors', 'overview', filters])
  })

  it('keeps the previous rows while a new view loads', () => {
    const { api } = fakeApi()

    expect(supplierOverviewQueryOptions(api).placeholderData).toBeDefined()
  })
})
