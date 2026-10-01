function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-cream px-6 text-center text-ink">
      <h1 className="font-serif text-[34px] leading-[1.15] text-ink sm:text-[44px]">Page not found.</h1>
      <p className="mt-3 max-w-[380px] text-[16px] text-ink/65">The page you’re looking for doesn’t exist.</p>
      <a
        href="/"
        className="mt-8 inline-flex h-[50px] items-center rounded-xl bg-yellow px-7 text-[15px] font-semibold text-ink outline-offset-4 focus-visible:outline-[3px] focus-visible:outline-ink"
      >
        Back to home
      </a>
    </main>
  )
}

export default NotFoundPage
