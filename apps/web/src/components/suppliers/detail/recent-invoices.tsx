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

/** The supplier's latest invoices, newest first. */
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Latest invoices</CardTitle>
        {shown ? (
          <p className="text-sm text-muted-foreground">{shown}</p>
        ) : null}
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table className="min-w-[36rem] table-fixed">
          <colgroup>
            <col className="w-[18%]" />
            <col className="w-[20%]" />
            <col className="w-[26%]" />
            <col className="w-[20%]" />
            <col className="w-[16%]" />
          </colgroup>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Invoice</TableHead>
              <TableHead>Company</TableHead>
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
                  <TableCell className="font-mono text-sm break-all">
                    {invoice.invoice_number ?? (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="truncate" title={invoice.company_name}>
                    {invoice.company_name}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
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
