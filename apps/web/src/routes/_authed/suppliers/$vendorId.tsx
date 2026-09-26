import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { SupplierDetailPanel } from '#/components/suppliers/detail/supplier-detail-panel'
import { useApi } from '#/lib/auth/auth'
import {
  isSupplierNotFound,
  supplierDetailQueryOptions,
} from '#/lib/api/vendors'

export const Route = createFileRoute('/_authed/suppliers/$vendorId')({
  component: SupplierPage,
  staticData: { title: 'Supplier' },
})

function SupplierPage() {
  const api = useApi()
  const navigate = useNavigate()
  const { vendorId } = Route.useParams()
  const supplier = useQuery(supplierDetailQueryOptions(api, vendorId))

  return (
    <SupplierDetailPanel
      supplier={supplier.data}
      loading={supplier.isPending}
      error={supplier.isError}
      notFound={isSupplierNotFound(supplier.error)}
      onBack={() => {
        void navigate({ to: '/suppliers' })
      }}
      onViewLines={() => {
        void navigate({
          to: '/invoice-lines',
          search: { vendor_id: vendorId },
        })
      }}
    />
  )
}
