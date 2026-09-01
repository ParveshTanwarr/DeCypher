import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Network, 
  FileText, 
  Home,
  Menu,
  X,
  Bot
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useChat } from '../../context/ChatContext';

export const Navbar: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { toggleChat, unreadCount } = useChat();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const navLinks = [
    { path: '/', label: 'Home', icon: Home },
    { path: '/graph', label: 'Investigate', icon: Network },
    { path: '/reports/A00001', label: 'Reports', icon: FileText },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800/80 bg-[#0d1117]/80 backdrop-blur-xl transition-colors duration-200 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* LEFT: DECyPHER LOGO & TAGLINE */}
        <Link 
          to="/" 
          id="navbar-logo-link"
          className="flex items-center gap-3 group focus:outline-none focus:ring-2 focus:ring-cyan-500 rounded-md p-1"
        >
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded flex items-center justify-center font-bold text-white shadow-[0_0_15px_rgba(6,182,212,0.4)] text-sm tracking-tighter">
            D
          </div>
          <div className="flex flex-col leading-none">
            <div className="flex items-center gap-1.5">
              <span className="text-base sm:text-lg font-bold tracking-tight text-white font-sans">
                DECyPHER
              </span>
            </div>
            <span className="text-[9px] uppercase tracking-[0.2em] text-cyan-500 font-semibold">
              Relationship Intelligence
            </span>
          </div>
        </Link>

        {/* CENTER: WORKSPACE STATUS BADGE */}
        <div className="hidden md:flex items-center gap-2 bg-slate-900/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-slate-700/40 shadow-inner">
          <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] animate-pulse" />
          <span className="text-[10px] font-mono text-slate-400">
            ACTIVE WORKSPACE: <strong className="text-slate-200 font-bold">OMEGA-7 (A00001)</strong>
          </span>
        </div>

        {/* RIGHT: NAVIGATION & SLEEK THEME SWITCH & GEMINI COPILOT */}
        <div className="hidden sm:flex items-center gap-4 lg:gap-6">
          <nav className="flex items-center gap-5 text-sm font-medium" aria-label="Main Navigation">
            {navLinks.map((link) => {
              const active = isActive(link.path);
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  id={`nav-link-${link.label.toLowerCase()}`}
                  className={`transition-colors cursor-pointer text-xs sm:text-sm tracking-wide ${
                    active
                      ? 'text-white border-b-2 border-cyan-500 pb-1 font-semibold'
                      : 'text-slate-400 hover:text-white pb-1'
                  }`}
                >
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* AI COPILOT BUTTON */}
          <button
            onClick={toggleChat}
            id="nav-gemini-btn"
            aria-label="Toggle Gemini AI Copilot"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 font-mono-code text-xs font-semibold transition-all shadow-[0_0_12px_rgba(6,182,212,0.15)] hover:shadow-[0_0_16px_rgba(6,182,212,0.3)] cursor-pointer"
          >
            <Bot className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden lg:inline">AI Copilot</span>
            <span className="lg:hidden">AI</span>
            {unreadCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-cyan-400 text-slate-950 text-[9px] font-bold">
                {unreadCount}
              </span>
            )}
          </button>

          {/* Sleek Minimal Toggle Switch */}
          <button
            id="theme-toggle-btn"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            title={`Current theme: ${theme} (Click to toggle)`}
            className="w-10 h-5 bg-slate-800 rounded-full relative flex items-center px-1 border border-slate-700 cursor-pointer transition-colors hover:border-slate-600 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <div 
              className={`w-3 h-3 bg-cyan-400 rounded-full shadow-[0_0_5px_rgba(34,211,238,0.5)] transition-transform duration-200 ${
                theme === 'dark' ? 'translate-x-0' : 'translate-x-5'
              }`} 
            />
          </button>
        </div>

        {/* Mobile menu toggle */}
        <div className="flex sm:hidden items-center gap-2">
          <button
            onClick={toggleChat}
            aria-label="Toggle AI Copilot"
            className="p-1.5 rounded border border-cyan-500/40 bg-cyan-500/10 text-cyan-400"
          >
            <Bot className="w-4 h-4" />
          </button>

          <button
            id="theme-toggle-mobile"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="w-8 h-4 bg-slate-800 rounded-full relative flex items-center px-0.5 border border-slate-700"
          >
            <div className={`w-2.5 h-2.5 bg-cyan-400 rounded-full ${theme === 'dark' ? 'translate-x-0' : 'translate-x-4'} transition-transform`} />
          </button>

          <button
            id="mobile-menu-btn"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
            className="p-1.5 rounded border border-slate-800 text-slate-400 hover:text-white"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div className="sm:hidden border-b border-slate-800 bg-[#0d1117] px-4 py-3 space-y-2">
          {navLinks.map((link) => {
            const active = isActive(link.path);
            return (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-2 px-3 py-2 text-sm rounded-md ${
                  active
                    ? 'bg-cyan-500/10 text-cyan-400 font-semibold border-l-2 border-cyan-500'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>{link.label}</span>
              </Link>
            );
          })}
          <div className="pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-400">
            ACTIVE WORKSPACE: OMEGA-7 (CLUSTER A00001)
          </div>
        </div>
      )}
    </header>
  );
};

