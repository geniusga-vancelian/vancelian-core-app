/**
 * Utility functions for markdown editor
 */

/**
 * Insert text at cursor position in a textarea
 */
export function insertAtCursor(
  textarea: HTMLTextAreaElement,
  insertText: string,
  wrapLeft?: string,
  wrapRight?: string,
  linePrefix?: string
) {
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const selectedText = textarea.value.substring(start, end)
  const textBefore = textarea.value.substring(0, start)
  const textAfter = textarea.value.substring(end)

  let newText = ''
  let newCursorPos = start

  if (linePrefix) {
    // Insert line prefix at the start of current line
    const lines = textBefore.split('\n')
    const currentLine = lines[lines.length - 1]
    const lineStart = textBefore.length - currentLine.length
    newText = textBefore.substring(0, lineStart) + linePrefix + textBefore.substring(lineStart) + insertText + textAfter
    newCursorPos = start + linePrefix.length + insertText.length
  } else if (wrapLeft && wrapRight) {
    // Wrap selected text (or insert at cursor)
    newText = textBefore + wrapLeft + (selectedText || insertText) + wrapRight + textAfter
    newCursorPos = start + wrapLeft.length + (selectedText || insertText).length + wrapRight.length
  } else {
    // Simple insert
    newText = textBefore + insertText + textAfter
    newCursorPos = start + insertText.length
  }

  textarea.value = newText
  textarea.setSelectionRange(newCursorPos, newCursorPos)
  textarea.focus()

  // Trigger onChange event
  const event = new Event('input', { bubbles: true })
  textarea.dispatchEvent(event)
}

