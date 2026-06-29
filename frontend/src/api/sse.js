/**
 * Low-level SSE client using fetch + ReadableStream.
 *
 * @param {string} url        - URL to POST to
 * @param {object} body       - JSON body to send
 * @param {AbortSignal} signal - AbortController.signal for cancellation
 * @param {(event: { event: string, data: object | null }) => void} onEvent
 *        Called for every SSE event received.
 * @returns {Promise<string>} the last meaningful event type seen
 *          ("complete", "cancelled", "judgment", or "error").
 */
export async function connectSSE(url, body, signal, onEvent) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    const errText = await response.text().catch(() => '')
    throw new Error(`SSE request failed (${response.status}): ${errText}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''
  let currentData = ''
  let lastMeaningfulEvent = null

  function flush() {
    if (currentData === '' && currentEvent === '') return null
    let data = null
    try {
      data = JSON.parse(currentData)
    } catch { /* ignore parse errors */ }
    const evt = { event: currentEvent, data }
    currentEvent = ''
    currentData = ''
    return evt
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // last incomplete line stays in buffer

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          currentData += line.slice(6)
        } else if (line === '') {
          // empty line = SSE event boundary
          const evt = flush()
          if (evt && evt.event) {
            lastMeaningfulEvent = evt.event
            onEvent(evt)
          }
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      return 'cancelled'
    }
    throw err
  }

  // Clean up any remaining data
  const final = flush()
  if (final && final.event) {
    lastMeaningfulEvent = final.event
  }

  // Return the last real event type we saw, fallback to "complete"
  return lastMeaningfulEvent || 'complete'
}
