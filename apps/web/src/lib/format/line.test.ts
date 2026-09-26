import { describe, expect, it } from 'vitest'
import { lineName } from './line'

describe('lineName', () => {
  it('prefers the item name', () => {
    expect(lineName({ item_name: 'Plus', description: 'Monthly plan' })).toBe(
      'Plus',
    )
  })

  it('falls back to the description', () => {
    expect(lineName({ item_name: null, description: 'Monthly plan' })).toBe(
      'Monthly plan',
    )
  })

  it('treats a blank field as missing', () => {
    expect(lineName({ item_name: '  ', description: 'Monthly plan' })).toBe(
      'Monthly plan',
    )
    expect(lineName({ item_name: 'Plus', description: '' })).toBe('Plus')
  })

  it('is null when the line has neither', () => {
    expect(lineName({ item_name: null, description: '' })).toBeNull()
  })
})
