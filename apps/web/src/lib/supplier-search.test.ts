import { describe, expect, it } from 'vitest'
import {
  applySupplierFilterChange,
  canSortBySpend,
  defaultOrder,
  resolveSupplierSort,
  validateSupplierSearch,
} from './supplier-search'
import type { CompanyRead } from './api/types'

function company(id: string, base_currency: string): CompanyRead {
  return {
    id,
    name: id,
    country_code: null,
    vat_number: null,
    base_currency,
    is_active: true,
    deactivated_at: null,
    spend_tree_id: null,
    spend_tree_name: null,
  }
}

describe('validateSupplierSearch', () => {
  it('reads every filter from the URL', () => {
    expect(
      validateSupplierSearch({
        q: 'google',
        company_id: 'c1',
        sort: 'invoice_count',
        order: 'asc',
        page: '3',
      }),
    ).toEqual({
      q: 'google',
      company_id: 'c1',
      sort: 'invoice_count',
      order: 'asc',
      page: 3,
    })
  })

  it('drops unknown sorts and orders', () => {
    expect(
      validateSupplierSearch({ sort: 'vat_number', order: 'sideways' }),
    ).toEqual({})
  })

  it('drops an empty search and the first page', () => {
    expect(validateSupplierSearch({ q: '', page: '1' })).toEqual({})
  })

  it('drops a page that is not a whole number', () => {
    expect(validateSupplierSearch({ page: '2.5' })).toEqual({})
  })
})

describe('applySupplierFilterChange', () => {
  it('returns to the first page when the view changes', () => {
    expect(
      applySupplierFilterChange({ q: 'a', page: 4 }, { sort: 'name' }),
    ).toEqual({ q: 'a', sort: 'name', page: undefined })
  })
})

describe('defaultOrder', () => {
  it('sorts names A to Z and figures largest first', () => {
    expect(defaultOrder('name')).toBe('asc')
    expect(defaultOrder('spend')).toBe('desc')
    expect(defaultOrder('last_invoice_date')).toBe('desc')
  })
})

describe('canSortBySpend', () => {
  const mixed = [company('dk', 'DKK'), company('eu', 'EUR')]

  it('allows it when every company shares a base currency', () => {
    expect(
      canSortBySpend([company('a', 'DKK'), company('b', 'DKK')], undefined),
    ).toBe(true)
  })

  it('refuses it across base currencies', () => {
    expect(canSortBySpend(mixed, undefined)).toBe(false)
  })

  it('allows it once one company is chosen', () => {
    expect(canSortBySpend(mixed, 'eu')).toBe(true)
  })
})

describe('resolveSupplierSort', () => {
  it('defaults to the largest spend first', () => {
    expect(resolveSupplierSort({}, true)).toEqual({
      sort: 'spend',
      order: 'desc',
    })
  })

  it('defaults to names A to Z when spend cannot be ordered', () => {
    expect(resolveSupplierSort({}, false)).toEqual({
      sort: 'name',
      order: 'asc',
    })
  })

  it('keeps the URL’s sort and order', () => {
    expect(
      resolveSupplierSort({ sort: 'invoice_count', order: 'asc' }, true),
    ).toEqual({ sort: 'invoice_count', order: 'asc' })
  })

  it('never asks for a spend order it cannot give', () => {
    expect(resolveSupplierSort({ sort: 'spend', order: 'asc' }, false)).toEqual(
      {
        sort: 'name',
        order: 'asc',
      },
    )
  })
})
