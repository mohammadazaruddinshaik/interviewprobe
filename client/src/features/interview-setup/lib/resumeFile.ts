export const MAX_RESUME_BYTES = 5 * 1024 * 1024
export const RESUME_ACCEPT = '.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'

/** Client-side check only (the backend re-validates the real file type). Returns an error message or null. */
export function validateResumeFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!name.endsWith('.pdf') && !name.endsWith('.docx')) return 'Choose a PDF or DOCX file.'
  if (file.size === 0) return 'That file is empty.'
  if (file.size > MAX_RESUME_BYTES) return 'Resumes must be 5 MB or smaller.'
  return null
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Identity of a selected file, to know whether a resume was already uploaded for an interview. */
export const fileKey = (file: File) => `${file.name}:${file.size}:${file.lastModified}`
