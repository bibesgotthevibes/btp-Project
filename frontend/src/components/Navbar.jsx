import Button from './Button'

export default function Navbar({ user, onLogout }) {
  return (
    <nav className="bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between shadow-sm sticky top-0 z-10">
      {/* Brand */}
      <div className="flex items-center gap-2.5">
        <span className="text-2xl leading-none">🏥</span>
        <span className="font-bold text-primary-500 text-xl tracking-tight">
          MedSimplify
        </span>
      </div>

      {/* User + Logout */}
      <div className="flex items-center gap-4">
        {user && (
          <span className="text-sm text-gray-500 hidden sm:block">
            Welcome,{' '}
            <span className="font-semibold text-gray-700">{user.name}</span>
          </span>
        )}
        <Button variant="outline" onClick={onLogout} className="py-2 px-4 text-sm">
          Logout
        </Button>
      </div>
    </nav>
  )
}
