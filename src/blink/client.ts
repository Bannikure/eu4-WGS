import { createClient } from '@blinkdotnew/sdk'

export const blink = createClient({
  projectId: import.meta.env.VITE_BLINK_PROJECT_ID || 'eu4-world-gen-rp9b45mi',
  publishableKey: import.meta.env.VITE_BLINK_PUBLISHABLE_KEY || 'blnk_pk_eK946OzlQapCPpU1EuMnUkAgsSwM-z01',
  authRequired: false,
  auth: { mode: 'managed' },
})
