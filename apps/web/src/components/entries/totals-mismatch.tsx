import { TriangleAlert } from 'lucide-react'
import {
  TableCell,
  TableRow,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '#/components/ui'
import { formatMoney } from '#/lib/format/format'
import type { VoucherGroupRead } from '#/lib/api/types'

interface Mismatch {
  documentTotal: string
  invoiceTotal: string
}

/** The two totals, formatted, when the document and the ERP disagree. */
function mismatchOf(group: VoucherGroupRead): Mismatch | null {
  if (
    group.totals_agree !== false ||
    group.document_total === null ||
    group.invoice_total === null
  ) {
    return null
  }
  return {
    documentTotal: formatMoney(group.document_total, group.invoice_currency),
    invoiceTotal: formatMoney(group.invoice_total, group.invoice_currency),
  }
}

/** Marks a voucher row whose document states a different total than the ERP posted. */
export function TotalsMismatchMarker({ group }: { group: VoucherGroupRead }) {
  const mismatch = mismatchOf(group)
  if (mismatch === null) {
    return null
  }
  const explanation = `The document states ${mismatch.documentTotal}; the ERP posted ${mismatch.invoiceTotal}.`

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span
            tabIndex={0}
            aria-label={`Document total differs from the ERP. ${explanation}`}
            className="inline-flex cursor-help text-warning outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        }
      >
        <TriangleAlert className="size-4" aria-hidden="true" />
      </TooltipTrigger>
      <TooltipContent>
        Document total differs from the ERP. {explanation}
      </TooltipContent>
    </Tooltip>
  )
}

/** A warning row above an expanded voucher's lines when the totals disagree. */
export function TotalsMismatchRow({ group }: { group: VoucherGroupRead }) {
  const mismatch = mismatchOf(group)
  if (mismatch === null) {
    return null
  }

  return (
    <TableRow className="bg-warning/5 hover:bg-warning/5">
      <TableCell />
      <TableCell colSpan={7} className="pl-8">
        <p role="note" className="flex items-start gap-2 text-sm">
          <TriangleAlert
            className="mt-0.5 size-4 shrink-0 text-warning"
            aria-hidden="true"
          />
          <span className="text-muted-foreground">
            These lines were read from a document stating a total of{' '}
            <span className="font-medium tabular-nums text-foreground">
              {mismatch.documentTotal}
            </span>
            , where the ERP posted{' '}
            <span className="font-medium tabular-nums text-foreground">
              {mismatch.invoiceTotal}
            </span>
            .
          </span>
        </p>
      </TableCell>
    </TableRow>
  )
}
