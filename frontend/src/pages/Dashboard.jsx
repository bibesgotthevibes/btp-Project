import { useState, useEffect } from 'react'
import Navbar from '../components/Navbar'
import Button from '../components/Button'
import OutputPanel from '../components/OutputPanel'
import Loader from '../components/Loader'
import api from '../api/axios'

export default function Dashboard({ user, setUser }) {
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('')
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [resultModel, setResultModel] = useState('')
  const [resultTokens, setResultTokens] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Fetch model list on mount
  useEffect(() => {
    api.get('/api/models')
      .then((res) => {
        const mods = res.data.models || []
        setModels(mods)
        // Pre-select the first accessible model
        const first = mods.find((m) => m.accessible)
        if (first) setSelectedModel(first.id)
      })
      .catch(() => {
        // Fallback: at least show the accessible model
        const fallback = [{ id: 'llama3.1-8b', name: 'Llama 3.1 8B', accessible: true }]
        setModels(fallback)
        setSelectedModel('llama3.1-8b')
      })
  }, [])

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  const simplify = async () => {
    if (!text.trim()) { setError('Please paste a discharge summary first.'); return }
    if (!selectedModel) { setError('Please select a model.'); return }

    const modelInfo = models.find((m) => m.id === selectedModel)
    if (modelInfo && !modelInfo.accessible) {
      setError('This model requires a higher-tier API key. Please select Llama 3.1 8B.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await api.post('/api/simplify', { text, model: selectedModel })
      setResult(res.data.result)
      setResultModel(res.data.model)
      setResultTokens(res.data.tokens)
    } catch (err) {
      setError(err.response?.data?.error || 'Simplification failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const clearAll = () => {
    setText('')
    setResult(null)
    setResultModel('')
    setResultTokens(null)
    setError('')
  }

  return (
    <div className="min-h-screen bg-[#F5F7FA] flex flex-col">
      <Navbar user={user} onLogout={logout} />

      <div className="flex-1 p-6 w-full max-w-6xl mx-auto">
        {/* Page title */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-800">
            Discharge Summary Simplifier
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Paste a clinical discharge summary and get a patient-friendly explanation in
            Indian Lay English, powered by Cerebras LLMs.
          </p>
        </div>

        {/* Two-column layout on large screens */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ── Input card ── */}
          <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-6 flex flex-col gap-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              Input
            </h2>

            {/* Model selector */}
            <div>
              <label className="text-sm font-semibold text-gray-600 block mb-1.5">
                AI Model
              </label>
              <div className="relative">
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-800
                    outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100
                    bg-white appearance-none cursor-pointer pr-10"
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id} disabled={!m.accessible}>
                      {m.accessible
                        ? `✓  ${m.name}`
                        : `🔒  ${m.name}  —  access not provided`}
                    </option>
                  ))}
                </select>
                {/* custom chevron */}
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  ▾
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-1.5">
                🔒 = requires higher-tier Cerebras API key &nbsp;·&nbsp; ✓ = available with your key
              </p>
            </div>

            {/* Textarea */}
            <div className="flex flex-col gap-1.5 flex-1">
              <label className="text-sm font-semibold text-gray-600">
                Discharge Summary
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste the patient's discharge summary here…&#10;&#10;Example: The patient was admitted with fever, chills, and productive cough…"
                rows={12}
                className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-800
                  outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100
                  resize-y leading-relaxed placeholder:text-gray-400"
              />
              <p className="text-xs text-gray-400 text-right">
                {text.trim().split(/\s+/).filter(Boolean).length} words
              </p>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 flex-wrap">
              <Button onClick={simplify} loading={loading} className="flex-1 py-3">
                ✨ Simplify Summary
              </Button>
              {(text || result) && (
                <Button variant="ghost" onClick={clearAll} className="py-3 px-4 text-sm">
                  Clear
                </Button>
              )}
            </div>
          </div>

          {/* ── Output card ── */}
          <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-6 flex flex-col gap-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              Simplified Output
            </h2>

            {loading ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-4 py-16 text-gray-400">
                <Loader size="lg" />
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-600">
                    Simplifying with Cerebras AI…
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    This usually takes a few seconds
                  </p>
                </div>
              </div>
            ) : (
              <OutputPanel result={result} model={resultModel} tokens={resultTokens} />
            )}
          </div>
        </div>

        {/* Info strip */}
        <div className="mt-6 bg-primary-50 border border-primary-100 rounded-xl px-5 py-3 flex items-start gap-3">
          <span className="text-primary-500 text-lg mt-0.5">ℹ</span>
          <p className="text-xs text-primary-600 leading-relaxed">
            <strong>Research use only.</strong> Simplified summaries are generated by AI and may contain errors.
            Always consult a qualified healthcare professional for medical advice.
          </p>
        </div>
      </div>
    </div>
  )
}
