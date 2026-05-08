import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import InputField from '../components/InputField'
import Button from '../components/Button'
import api from '../api/axios'

const Illustration = () => (
  <div className="text-center select-none">
    <div className="text-6xl mb-5">🏥</div>
    <h2 className="text-xl font-bold mb-3">MedSimplify</h2>
    <p className="text-violet-100 text-sm leading-relaxed">
      Making complex medical discharge summaries easy to understand — for
      patients and their families.
    </p>
    <div className="mt-8 grid grid-cols-2 gap-3 text-xs">
      {['Cloud & Local AI', 'JWT Auth', 'PDF Export', 'Indian Lay English'].map((f) => (
        <div
          key={f}
          className="bg-white/15 rounded-xl px-3 py-2 font-medium text-white"
        >
          {f}
        </div>
      ))}
    </div>
  </div>
)

export default function Login({ setUser }) {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [serverError, setServerError] = useState('')

  const handle = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const validate = () => {
    const errs = {}
    if (!form.email.trim()) errs.email = 'Email is required.'
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Enter a valid email.'
    if (!form.password) errs.password = 'Password is required.'
    return errs
  }

  const submit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }

    setLoading(true)
    setServerError('')
    try {
      const res = await api.post('/api/auth/login', form)
      localStorage.setItem('token', res.data.token)
      setUser(res.data.user)
      navigate('/dashboard')
    } catch (err) {
      setServerError(err.response?.data?.error || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthCard illustration={<Illustration />}>
      {/* Header */}
      <div className="mb-8">
        <p className="text-primary-500 text-sm font-semibold mb-1">Welcome back 👋</p>
        <h1 className="text-2xl font-bold text-gray-800">Sign in to your account</h1>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <InputField
          label="Email address"
          name="email"
          type="email"
          placeholder="you@example.com"
          value={form.email}
          onChange={handle}
          error={errors.email}
          autoComplete="email"
        />
        <InputField
          label="Password"
          name="password"
          type="password"
          placeholder="••••••••"
          value={form.password}
          onChange={handle}
          error={errors.password}
          autoComplete="current-password"
        />

        {/* Remember me */}
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            className="w-4 h-4 rounded accent-primary-500 cursor-pointer"
          />
          <span className="text-sm text-gray-500">Remember me</span>
        </label>

        {/* Server error */}
        {serverError && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
            {serverError}
          </div>
        )}

        <Button type="submit" loading={loading} className="w-full mt-1 py-3">
          Sign in
        </Button>
      </form>

      <p className="text-sm text-center text-gray-500 mt-6">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="text-primary-500 font-semibold hover:underline">
          Create one
        </Link>
      </p>
    </AuthCard>
  )
}
