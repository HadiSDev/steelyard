import { keepPreviousData, queryOptions } from '@tanstack/react-query'
import { ApiError } from './api-client'
import type { ApiClient } from './api-client'
import type {
  Page,
  SupplierFilters,
  VendorDetailRead,
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

/** Whether the request failed because the supplier is not one of the organization's. */
export function isSupplierNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}

/** One supplier with its figures, categories and latest invoices (`GET /vendors/{id}/detail`). */
export function supplierDetailQueryOptions(api: ApiClient, vendorId: string) {
  return queryOptions({
    queryKey: ['vendors', 'detail', vendorId],
    queryFn: () =>
      api.get<VendorDetailRead>(
        `/api/v1/vendors/${encodeURIComponent(vendorId)}/detail`,
      ),
    retry: (failures, error) => !isSupplierNotFound(error) && failures < 1,
  })
}
