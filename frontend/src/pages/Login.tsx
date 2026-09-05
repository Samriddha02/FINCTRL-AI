import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      localStorage.setItem('finctrl_auth', 'true');
      navigate('/dashboard');
    }, 500);
  };

  const handleDemo = () => {
    setEmail('demo@finctrl.ai');
    setPassword('demo');
    setIsLoading(true);
    setTimeout(() => {
      localStorage.setItem('finctrl_auth', 'true');
      navigate('/dashboard');
    }, 500);
  };

  return (
    <div className="w-full h-full flex flex-col">
      <main className="flex-grow flex flex-col md:flex-row w-full min-h-screen">
        {/* Left Side: Branding */}
        <section className="hidden md:flex flex-col w-[45%] bg-primary-container relative overflow-hidden px-12 py-16 justify-between">
          <div className="absolute inset-0 pattern-dots opacity-20 pointer-events-none"></div>
          <div className="relative z-10">
            <h1 className="text-white text-4xl font-bold mb-4">FINCTRL-AI</h1>
            <p className="text-inverse-primary text-lg">AI Finance Control</p>
          </div>
        </section>

        {/* Right Side: Login Form */}
        <section className="flex-1 flex flex-col justify-center px-8 md:px-16 lg:px-24 xl:px-32 relative">
          <div className="w-full max-w-md mx-auto">
            <h2 className="font-page-title text-page-title text-text-primary mb-2">Welcome Back</h2>
            <p className="font-body-table text-text-secondary mb-8">Sign in to access your financial intelligence workspace.</p>
            
            <form className="space-y-5" onSubmit={handleLogin}>
              <div>
                <label className="block font-label-sm text-text-primary mb-1.5" htmlFor="email">Email Address</label>
                <div className="relative">
                  <input className="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-colors text-sm" id="email" placeholder="name@company.com" required type="email" value={email} onChange={e => setEmail(e.target.value)} />
                </div>
              </div>
              <div>
                <label className="block font-label-sm text-text-primary mb-1.5" htmlFor="password">Password</label>
                <div className="relative">
                  <input className="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-colors text-sm" id="password" placeholder="••••••••" required type="password" value={password} onChange={e => setPassword(e.target.value)} />
                </div>
              </div>
              <button className="w-full py-2.5 bg-brand-blue hover:bg-action-blue-dark text-white rounded-lg font-semibold text-sm transition-colors shadow-sm disabled:opacity-50" disabled={isLoading} type="submit">
                {isLoading ? 'Signing In...' : 'Sign In'}
              </button>
            </form>
            <div className="mt-4">
              <button onClick={handleDemo} className="w-full py-2.5 bg-surface border border-brand-blue text-brand-blue hover:bg-brand-blue hover:text-white rounded-lg font-semibold text-sm transition-colors shadow-sm" type="button">
                Demo Account
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
