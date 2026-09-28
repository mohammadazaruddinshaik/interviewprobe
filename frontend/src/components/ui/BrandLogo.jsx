import { useTheme } from '../../hooks/useTheme.js'

// The one way every page renders the InterviewProbe wordmark, so the logo
// is the same size and swaps correctly everywhere. Both files are fully
// outlined vectors (no <text>), because an SVG loaded through <img> can't
// use the page's web fonts and would silently fall back to Arial. The
// swap follows the real theme (useTheme), never a CSS filter or invert.
const SIZES = {
  sm: 'h-6',
  md: 'h-6 sm:h-7',
}

function BrandLogo({ size = 'md', collapse = false, className = '' }) {
  const { theme } = useTheme()
  const wordmark = (
    <img
      src={theme === 'dark' ? '/assets/brand/logo-dark.svg' : '/assets/brand/logo-light.svg'}
      alt="InterviewProbe"
      className={`w-auto ${SIZES[size] ?? SIZES.md} ${collapse ? 'hidden sm:block' : ''} ${className}`}
    />
  )

  if (!collapse) return wordmark

  // `collapse`: below `sm` show only the mark, for bars whose right side
  // carries real controls that must never be pushed off-screen.
  return (
    <>
      <img src="/assets/brand/logo-icon.svg" alt="InterviewProbe" className="h-6 w-auto sm:hidden" />
      {wordmark}
    </>
  )
}

export default BrandLogo
