import { describe, expect, it, vi } from 'vitest'
import {
  isSupplierNotFound,
  supplierDetailQueryOptions,
  supplierOverviewQueryOptions,
} from './vendors'
import { ApiError } from './api-client'
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

describe('supplierDetailQueryOptions', () => {
  it('asks the detail endpoint for the one supplier', async () => {
    const { api, get } = fakeApi()
    const options = supplierDetailQueryOptions(api, 'v/1')

    await options.queryFn!({} as never)

    expect(get).toHaveBeenCalledWith('/api/v1/vendors/v%2F1/detail')
    expect(options.queryKey).toEqual(['vendors', 'detail', 'v/1'])
  })

  it('does not retry a supplier that is not the organization’s', () => {
    const { api } = fakeApi()
    const retry = supplierDetailQueryOptions(api, 'v1').retry as (
      failures: number,
      error: unknown,
    ) => boolean

    expect(retry(0, new ApiError(404, 'not found'))).toBe(false)
    expect(retry(0, new ApiError(500, 'failed'))).toBe(true)
    expect(retry(1, new ApiError(500, 'failed'))).toBe(false)
  })

  it('tells a missing supplier from any other failure', () => {
    expect(isSupplierNotFound(new ApiError(404, 'not found'))).toBe(true)
    expect(isSupplierNotFound(new ApiError(500, 'failed'))).toBe(false)
    expect(isSupplierNotFound(new Error('offline'))).toBe(false)
  })
})
