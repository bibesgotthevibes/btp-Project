export default function Loader({ size = 'md' }) {
  const sizeClass =
    size === 'sm' ? 'w-4 h-4 border-2' :
    size === 'lg' ? 'w-10 h-10 border-[3px]' :
    'w-6 h-6 border-2'

  return (
    <span
      className={`inline-block ${sizeClass} border-primary-200 border-t-primary-500 rounded-full animate-spin`}
      role="status"
      aria-label="Loading"
    />
  )
}
