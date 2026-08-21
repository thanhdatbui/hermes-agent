import { atom } from 'nanostores'

import { persistBoolean, storedBoolean } from '@/lib/storage'

// The old default exposed a low-contrast artwork layer behind translucent chat
// surfaces. Keep the preference, but make the clean surface the default for
// existing installs as well as fresh ones.
const KEY = 'hermes.desktop.backdrop.v2'

/** Whether the faint statue image renders behind the chat transcript. */
export const $backdrop = atom(storedBoolean(KEY, false))

$backdrop.subscribe(on => persistBoolean(KEY, on))

export function setBackdrop(on: boolean) {
  $backdrop.set(on)
}
