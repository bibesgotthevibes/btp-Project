import Loader from './Loader'

const VARIANTS = {
  primary:
    'bg-primary-500 hover:bg-primary-600 active:bg-primary-700 text-white shadow-md hover:shadow-lg',
  outline:
    'border-2 border-primary-500 text-primary-500 hover:bg-primary-50 active:bg-primary-100',
  danger:
    'bg-red-500 hover:bg-red-600 text-white shadow-sm',
  ghost:
    'text-gray-500 hover:text-gray-800 hover:bg-gray-100',
}

export default function Button({
  children,
  loading = false,
  variant = 'primary',
  className = '',
  ...props
}) {
  return (
    <button
      className={`
        inline-flex items-center justify-center gap-2
        rounded-xl font-semibold px-5 py-2.5
        transition-all duration-150
        disabled:opacity-60 disabled:cursor-not-allowed
        ${VARIANTS[variant] ?? VARIANTS.primary}
        ${className}
      `}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && <Loader size="sm" />}
      {children}
    </button>
  )
}
