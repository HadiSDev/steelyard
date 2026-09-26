import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui'
import { formatCount, formatDay } from '#/lib/format/format'
import type {
  SortOrder,
  SupplierSort,
  VendorOverviewRead,
} from '#/lib/api/types'
import { SortHeader } from './sort-header'
import { SupplierCountry } from './supplier-country'
import { SupplierDescription } from './supplier-description'
import { SupplierSpend } from './supplier-spend'

/** Fixed column widths, so paging or sorting never reflows the table. */
function SupplierColumns() {
  return (
    <colgroup>
      <col className="w-[21%]" />
      <col className="w-[12%]" />
      <col className="w-[12%]" />
      <col className="w-[22%]" />
      <col className="w-[8%]" />
      <col className="w-[14%]" />
      <col className="w-[11%]" />
    </colgroup>
  )
}

export interface SupplierTableProps {
  suppliers: Array<VendorOverviewRead>
  sort: SupplierSort
  order: SortOrder
  /** Whether spend can be sorted; false when it would compare currencies. */
  spendSortable: boolean
  onSort: (column: SupplierSort) => void
  onSelect: (supplier: VendorOverviewRead) => void
}

/** The organization's suppliers, one row each, with their figures. */
export function SupplierTable({
  suppliers,
  sort,
  order,
  spendSortable,
  onSort,
  onSelect,
}: SupplierTableProps) {
  const header = { sort, order, onSort }

  return (
    <Table className="table-fixed">
      <SupplierColumns />
      <TableHeader>
        <TableRow>
          <SortHeader label="Supplier" column="name" {...header} />
          <TableHead>Country</TableHead>
          <TableHead>VAT number</TableHead>
          <TableHead>What they sell</TableHead>
          <SortHeader
            label="Invoices"
            column="invoice_count"
            align="right"
            {...header}
          />
          <SortHeader
            label="Spend"
            column="spend"
            align="right"
            sortable={spendSortable}
            {...header}
          />
          <SortHeader
            label="Last invoice"
            column="last_invoice_date"
            {...header}
          />
        </TableRow>
      </TableHeader>
      <TableBody>
        {suppliers.map((supplier) => (
          <TableRow
            key={supplier.id}
            className="cursor-pointer"
            onClick={() => onSelect(supplier)}
          >
            <TableCell className="break-words">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation()
                  onSelect(supplier)
                }}
                aria-label={`View spend lines for ${supplier.name}`}
                className="text-left font-medium outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
              >
                {supplier.name}
              </button>
            </TableCell>
            <TableCell>
              <SupplierCountry code={supplier.country_code} />
            </TableCell>
            <TableCell className="font-mono text-sm tabular-nums break-all text-muted-foreground">
              {supplier.vat_number ?? '—'}
            </TableCell>
            <TableCell>
              <SupplierDescription description={supplier.description} />
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCount(supplier.invoice_count)}
            </TableCell>
            <TableCell className="text-right">
              <SupplierSpend spend={supplier.spend} />
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {formatDay(supplier.last_invoice_date)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
