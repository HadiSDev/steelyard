import { Button, Card, Skeleton } from '#/components/ui'
import type { VendorDetailRead } from '#/lib/api/types'
import { CategoryBreakdown } from './category-breakdown'
import { RecentInvoices } from './recent-invoices'
import { SupplierFigures } from './supplier-figures'
import { SupplierHeader } from './supplier-header'

function LoadingState() {
  return (
    <div data-testid="supplier-loading" className="flex flex-col gap-6">
      <Skeleton className="h-9 w-72" />
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-24 w-full" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-72 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    </div>
  )
}

function Message({
  title,
  body,
  onBack,
}: {
  title: string
  body: string
  onBack: () => void
}) {
  return (
    <Card className="p-8 text-center">
      <h2 className="font-display text-base font-medium">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
        {body}
      </p>
      <div className="mt-4">
        <Button variant="outline" onClick={onBack}>
          Back to suppliers
        </Button>
      </div>
    </Card>
  )
}

export interface SupplierDetailPanelProps {
  supplier: VendorDetailRead | undefined
  loading: boolean
  error: boolean
  /** The supplier is not one the organization has bought from. */
  notFound: boolean
  onBack: () => void
  onViewLines: () => void
}

/** One supplier: who it is, what was spent with it, on what, and its latest invoices. */
export function SupplierDetailPanel({
  supplier,
  loading,
  error,
  notFound,
  onBack,
  onViewLines,
}: SupplierDetailPanelProps) {
  if (notFound) {
    return (
      <Message
        title="Supplier not found"
        body="None of your companies has an invoice from this supplier."
        onBack={onBack}
      />
    )
  }
  if (error) {
    return (
      <Message
        title="Couldn’t load this supplier"
        body="The request to the web API failed. Check that it is running and reachable, then reload."
        onBack={onBack}
      />
    )
  }
  if (loading || supplier === undefined) {
    return <LoadingState />
  }

  return (
    <div className="flex flex-col gap-6">
      <SupplierHeader
        supplier={supplier}
        onBack={onBack}
        onViewLines={onViewLines}
      />
      <SupplierFigures supplier={supplier} />
      <div className="grid items-start gap-6 lg:grid-cols-2">
        <CategoryBreakdown categories={supplier.categories} />
        <RecentInvoices
          invoices={supplier.recent_invoices}
          invoiceCount={supplier.invoice_count}
        />
      </div>
    </div>
  )
}
