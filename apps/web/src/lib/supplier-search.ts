import type {
  CompanyRead,
  SortOrder,
  SupplierFilters,
  SupplierSort,
} from './api/types'

const SORTS: ReadonlyArray<SupplierSort> = [
  'name',
  'spend',
  'invoice_count',
  'last_invoice_date',
]

const ORDERS: ReadonlyArray<SortOrder> = ['asc', 'desc']

function str(value: unknown): string | undefined {
  return typeof value === 'string' && value !== '' ? value : undefined
}

function oneOf<T extends string>(
  value: unknown,
  allowed: ReadonlyArray<T>,
): T | undefined {
  return typeof value === 'string' &&
    (allowed as ReadonlyArray<string>).includes(value)
    ? (value as T)
    : undefined
}

/** Parse the Suppliers route's search params, dropping unknown values. */
export function validateSupplierSearch(
  search: Record<string, unknown>,
): SupplierFilters {
  const page = Number(search.page)
  return {
    q: str(search.q),
    company_id: str(search.company_id),
    sort: oneOf(search.sort, SORTS),
    order: oneOf(search.order, ORDERS),
    page: Number.isInteger(page) && page > 1 ? page : undefined,
  }
}

/** Apply a search, filter or sort change, returning to the first page. */
export function applySupplierFilterChange(
  filters: SupplierFilters,
  changes: Partial<SupplierFilters>,
): SupplierFilters {
  return { ...filters, ...changes, page: undefined }
}

/** The order a column sorts in when first chosen: names A–Z, figures largest first. */
export function defaultOrder(sort: SupplierSort): SortOrder {
  return sort === 'name' ? 'asc' : 'desc'
}

/** Whether the listed companies share one base currency, so their spend can be ordered. */
export function canSortBySpend(
  companies: Array<CompanyRead>,
  companyId: string | undefined,
): boolean {
  const listed =
    companyId === undefined
      ? companies
      : companies.filter((company) => company.id === companyId)
  return new Set(listed.map((company) => company.base_currency)).size <= 1
}

/** The sort in effect: the URL's, else spend when it can be ordered, else name. */
export function resolveSupplierSort(
  filters: SupplierFilters,
  spendSortable: boolean,
): { sort: SupplierSort; order: SortOrder } {
  const requested =
    filters.sort === 'spend' && !spendSortable ? undefined : filters.sort
  const sort = requested ?? (spendSortable ? 'spend' : 'name')
  const order =
    requested === undefined
      ? defaultOrder(sort)
      : (filters.order ?? defaultOrder(sort))
  return { sort, order }
}
