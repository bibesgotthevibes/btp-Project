/**
 * Split-screen card used by Login and Register pages.
 * Left side: form content (children)
 * Right side: gradient illustration panel
 */
export default function AuthCard({ children, illustration }) {
  return (
    <div className="min-h-screen bg-[#F5F7FA] flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-card overflow-hidden flex">
        {/* ── Left: Form ── */}
        <div className="flex-1 px-10 py-12 flex flex-col justify-center">
          {children}
        </div>

        {/* ── Right: Gradient panel ── */}
        <div className="hidden md:flex w-80 flex-col items-center justify-center bg-gradient-to-br from-primary-500 to-violet-400 p-10 text-white flex-shrink-0">
          {illustration}
        </div>
      </div>
    </div>
  )
}
