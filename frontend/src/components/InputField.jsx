export default function InputField({
  label,
  error,
  className = '',
  ...props
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {label && (
        <label className="text-sm font-semibold text-gray-600">{label}</label>
      )}
      <input
        className={`
          w-full rounded-xl border px-4 py-3 text-sm text-gray-800
          outline-none transition-all duration-150 bg-white
          placeholder:text-gray-400
          ${
            error
              ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-100'
              : 'border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-100'
          }
        `}
        {...props}
      />
      {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
    </div>
  )
}
