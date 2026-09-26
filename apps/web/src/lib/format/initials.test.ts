import { describe, expect, it } from 'vitest'
import { initials } from './initials'

describe('initials', () => {
  it('takes the first letter of the first two words', () => {
    expect(initials('Acme Holding A/S')).toBe('AH')
  })

  it('takes the first two letters of a single word', () => {
    expect(initials('acme')).toBe('AC')
  })

  it('marks an empty name rather than showing nothing', () => {
    expect(initials('   ')).toBe('?')
  })
})
