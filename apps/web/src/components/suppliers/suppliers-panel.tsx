import { Button, Card, Pagination, Skeleton } from '#/components/ui'
import type {
  CompanyRead,
  Page,
  SortOrder,
  SupplierFilters,
  SupplierSort,
  VendorOverviewRead,
} from '#/lib/api/types'
import { SupplierTable } from './supplier-table'
import { SuppliersToolbar } from './suppliers-toolbar'

function LoadingState() {
  return (
    <div data-testid="suppliers-loading" className="flex flex-col gap-3">
      {Array.from({ length: 8 }).map((_, index) => (
        <Skeleton key={index} className="h-14 rounded-md" />
      ))}
    </div>
  )
}

function ErrorState() {
  return (
    <Card className="p-8 text-center">
      <h2 className="font-display text-base font-medium">
        Couldn’t load your suppliers
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
        The request to the web API failed. Check that it is running and
        reachable, then reload.
      </p>
    </Card>
  )
}

function EmptyState({
  filtered,
  onClear,
}: {
  filtered: boolean
  onClear: () => void
}) {
  if (!filtered) {
    return (
      <Card className="p-8 text-center">
        <h2 className="font-display text-base font-medium">No suppliers yet</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          Suppliers appear here once invoices are synced from a connected ERP.
        </p>
      </Card>
    )
  }
  return (
    <Card className="p-8 text-center">
      <h2 className="font-display text-base font-medium">No suppliers match</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
        Try another name or VAT number, or show every company.
      </p>
      <div className="mt-4">
        <Button variant="outline" onClick={onClear}>
          Clear search
        </Button>
      </div>
    </Card>
  )
}

export interface SuppliersPanelProps {
  result: Page<VendorOverviewRead> | undefined
  loading: boolean
  error: boolean
  filters: SupplierFilters
  /** The sort in effect, including the default when the URL names none. */
  sort: SupplierSort
  order: SortOrder
  spendSortable: boolean
  companies: Array<CompanyRead>
  onFiltersChange: (changes: Partial<SupplierFilters>) => void
  onClearFilters: () => void
  onSort: (column: SupplierSort) => void
  onPageChange: (page: number) => void
  onSelect: (supplier: VendorOverviewRead) => void
}

/** The Suppliers page body: search, the table, paging, and its states. */
export function SuppliersPanel({
  result,
  loading,
  error,
  filters,
  sort,
  order,
  spendSortable,
  companies,
  onFiltersChange,
  onClearFilters,
  onSort,
  onPageChange,
  onSelect,
}: SuppliersPanelProps) {
  const filtered = filters.q !== undefined || filters.company_id !== undefined
  const pageCount = result
    ? Math.max(1, Math.ceil(result.total / result.page_size))
    : 1

  function body() {
    if (error) {
      return <ErrorState />
    }
    if (loading || !result) {
      return <LoadingState />
    }
    if (result.items.length === 0) {
      return <EmptyState filtered={filtered} onClear={onClearFilters} />
    }
    return (
      <>
        <SupplierTable
          suppliers={result.items}
          sort={sort}
          order={order}
          spendSortable={spendSortable}
          onSort={onSort}
          onSelect={onSelect}
        />
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {result.total} supplier{result.total === 1 ? '' : 's'}
          </p>
          <Pagination
            page={result.page}
            pageCount={pageCount}
            onPageChange={onPageChange}
          />
        </div>
      </>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <SuppliersToolbar
        filters={filters}
        companies={companies}
        onChange={onFiltersChange}
      />
      {body()}
    </div>
  )
}
