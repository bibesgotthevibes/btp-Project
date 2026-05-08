import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import InputField from '../components/InputField'
import Button from '../components/Button'
import api from '../api/axios'

const Illustration = () => (
  <div className="text-center select-none">
    <div className="text-6xl mb-5">🩺</div>
    <h2 className="text-xl font-bold mb-3">Join MedSimplify</h2>
    <p className="text-violet-100 text-sm leading-relaxed">
      Create an account to simplify medical discharge summaries using
      state-of-the-art AI — making healthcare accessible for everyone.
    </p>
    <div className="mt-8 space-y-2 text-sm text-left">
      {[
        '✓ Powered by Cloud & Local LLMs',
        '✓ Indian Lay English output',
        '✓ Downloadable PDF reports',
        '✓ Secure JWT authentication',
      ].map((item) => (
        <p key={item} className="text-violet-100 font-medium">
          {item}
        </p>
      ))}
    </div>
  </div>
)

export default function Register({ setUser }) {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirm: '',
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [serverError, setServerError] = useState('')

  const handle = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const validate = () => {
    const errs = {}
    if (!form.name.trim()) errs.name = 'Name is required.'
    if (!form.email.trim()) errs.email = 'Email is required.'
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Enter a valid email.'
    if (!form.password) errs.password = 'Password is required.'
    else if (form.password.length < 8) errs.password = 'Minimum 8 characters.'
    if (form.confirm !== form.password) errs.confirm = 'Passwords do not match.'
    return errs
  }

  const submit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }

    setLoading(true)
    setServerError('')
    try {
      await api.post('/api/auth/register', {
        name: form.name,
        email: form.email,
        password: form.password,
      })
      // Auto-login after successful registration
      const res = await api.post('/api/auth/login', {
        email: form.email,
        password: form.password,
      })
      localStorage.setItem('token', res.data.token)
      setUser(res.data.user)
      navigate('/dashboard')
    } catch (err) {
      setServerError(err.response?.data?.error || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthCard illustration={<Illustration />}>
      {/* Header */}
      <div className="mb-7">
        <p className="text-primary-500 text-sm font-semibold mb-1">Get started free</p>
        <h1 className="text-2xl font-bold text-gray-800">Create your account</h1>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3.5" noValidate>
        <InputField
          label="Full Name"
          name="name"
          type="text"
          placeholder="John Doe"
          value={form.name}
          onChange={handle}
          error={errors.name}
          autoComplete="name"
        />
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
          placeholder="Min. 8 characters"
          value={form.password}
          onChange={handle}
          error={errors.password}
          autoComplete="new-password"
        />
        <InputField
          label="Confirm Password"
          name="confirm"
          type="password"
          placeholder="Re-enter password"
          value={form.confirm}
          onChange={handle}
          error={errors.confirm}
          autoComplete="new-password"
        />

        {serverError && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
            {serverError}
          </div>
        )}

        <Button type="submit" loading={loading} className="w-full mt-1.5 py-3">
          Create account
        </Button>
      </form>

      <p className="text-sm text-center text-gray-500 mt-5">
        Already have an account?{' '}
        <Link to="/login" className="text-primary-500 font-semibold hover:underline">
          Sign in
        </Link>
      </p>
    </AuthCard>
  )
}
