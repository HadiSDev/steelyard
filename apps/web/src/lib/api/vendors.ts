import { keepPreviousData, queryOptions } from '@tanstack/react-query'
import type { ApiClient } from './api-client'
import type {
  Page,
  SupplierFilters,
  VendorOverviewRead,
  VendorRead,
} from './types'

/** The org's suppliers (`GET /vendors`). */
export function vendorsQueryOptions(
  api: ApiClient,
  { q }: { q?: string } = {},
) {
  return queryOptions({
    queryKey: ['vendors', { q: q || undefined }],
    queryFn: () =>
      api.get<Page<VendorRead>>('/api/v1/vendors', { q: q || undefined }),
  })
}

/** The org's suppliers with their figures, as the Suppliers page lists them (`GET /vendors/overview`). */
export function supplierOverviewQueryOptions(
  api: ApiClient,
  filters: SupplierFilters = {},
) {
  return queryOptions({
    queryKey: ['vendors', 'overview', filters],
    queryFn: () =>
      api.get<Page<VendorOverviewRead>>('/api/v1/vendors/overview', {
        ...filters,
      }),
    placeholderData: keepPreviousData,
  })
}
