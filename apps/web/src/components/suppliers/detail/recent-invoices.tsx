import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui'
import type { BadgeProps } from '#/components/ui'
import { formatDay, formatMoney } from '#/lib/format/format'
import type { InvoiceStatus, VendorInvoiceRead } from '#/lib/api/types'

const STATUS_BADGES: Record<
  InvoiceStatus,
  { label: string; variant: BadgeProps['variant'] }
> = {
  uncategorized: { label: 'Uncategorized', variant: 'default' },
  categorized: { label: 'Categorized', variant: 'info' },
  verified: { label: 'Verified', variant: 'success' },
}

function InvoiceNumber({ invoice }: { invoice: VendorInvoiceRead }) {
  if (invoice.invoice_number) {
    return <span className="font-mono">{invoice.invoice_number}</span>
  }
  if (invoice.voucher_number) {
    return (
      <span className="text-muted-foreground">
        Voucher <span className="font-mono">{invoice.voucher_number}</span>
      </span>
    )
  }
  return <span className="text-muted-foreground">—</span>
}

/** The supplier's latest invoices, newest first; the company is named only when there are several. */
export function RecentInvoices({
  invoices,
  invoiceCount,
}: {
  invoices: Array<VendorInvoiceRead>
  invoiceCount: number
}) {
  const shown =
    invoiceCount > invoices.length
      ? `The latest ${invoices.length} of ${invoiceCount}`
      : undefined
  const showCompany =
    new Set(invoices.map((invoice) => invoice.company_name)).size > 1

  return (
    <Card>
      <CardHeader>
        <CardTitle>Latest invoices</CardTitle>
        {shown ? (
          <p className="text-sm text-muted-foreground">{shown}</p>
        ) : null}
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Invoice</TableHead>
              {showCompany ? <TableHead>Company</TableHead> : null}
              <TableHead className="text-right">Total</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invoices.map((invoice) => {
              const badge = STATUS_BADGES[invoice.status]
              return (
                <TableRow key={invoice.id}>
                  <TableCell className="whitespace-nowrap">
                    {formatDay(invoice.invoice_date)}
                  </TableCell>
                  <TableCell className="text-sm break-all">
                    <InvoiceNumber invoice={invoice} />
                  </TableCell>
                  {showCompany ? (
                    <TableCell className="break-words">
                      {invoice.company_name}
                    </TableCell>
                  ) : null}
                  <TableCell className="text-right font-mono whitespace-nowrap tabular-nums">
                    {invoice.total === null ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      formatMoney(invoice.total, invoice.currency)
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={badge.variant}>{badge.label}</Badge>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
