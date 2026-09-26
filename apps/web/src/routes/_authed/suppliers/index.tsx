import * as React from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { SuppliersPanel } from '#/components/suppliers/suppliers-panel'
import { useApi } from '#/lib/auth/auth'
import { companiesQueryOptions } from '#/lib/api/companies'
import { supplierOverviewQueryOptions } from '#/lib/api/vendors'
import type { SupplierFilters, SupplierSort } from '#/lib/api/types'
import {
  applySupplierFilterChange,
  canSortBySpend,
  defaultOrder,
  resolveSupplierSort,
  validateSupplierSearch,
} from '#/lib/supplier-search'

export const Route = createFileRoute('/_authed/suppliers/')({
  component: SuppliersPage,
  staticData: { title: 'Suppliers' },
  validateSearch: validateSupplierSearch,
})

function SuppliersPage() {
  const api = useApi()
  const navigate = useNavigate({ from: Route.fullPath })
  const filters = Route.useSearch()

  const companies = useQuery(companiesQueryOptions(api))
  const spendSortable = canSortBySpend(companies.data ?? [], filters.company_id)
  const { sort, order } = resolveSupplierSort(filters, spendSortable)

  const suppliers = useQuery({
    ...supplierOverviewQueryOptions(api, { ...filters, sort, order }),
    enabled: companies.isSuccess,
  })

  const onFiltersChange = React.useCallback(
    (changes: Partial<SupplierFilters>) => {
      void navigate({ search: applySupplierFilterChange(filters, changes) })
    },
    [filters, navigate],
  )

  function onSort(column: SupplierSort) {
    if (column !== sort) {
      onFiltersChange({ sort: column, order: defaultOrder(column) })
      return
    }
    onFiltersChange({ sort: column, order: order === 'asc' ? 'desc' : 'asc' })
  }

  return (
    <SuppliersPanel
      result={suppliers.data}
      loading={companies.isPending || suppliers.isPending}
      error={companies.isError || suppliers.isError}
      filters={filters}
      sort={sort}
      order={order}
      spendSortable={spendSortable}
      companies={companies.data ?? []}
      onFiltersChange={onFiltersChange}
      onClearFilters={() => {
        void navigate({ search: {} })
      }}
      onSort={onSort}
      onPageChange={(page) => {
        void navigate({ search: { ...filters, page } })
      }}
      onSelect={(supplier) => {
        void navigate({
          to: '/suppliers/$vendorId',
          params: { vendorId: supplier.id },
        })
      }}
    />
  )
}
