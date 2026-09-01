import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { ChatProvider } from './context/ChatContext';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { GeminiChatDrawer } from './components/chat/GeminiChatDrawer';
import { HomePage } from './pages/HomePage';
import { GraphPage } from './pages/GraphPage';
import { ActorPage } from './pages/ActorPage';
import { ReportPage } from './pages/ReportPage';
import { LoadingIndicator } from './components/ui/LoadingIndicator';

export default function App() {
  return (
    <ThemeProvider>
      <ChatProvider>
        <BrowserRouter>
          <div className="min-h-screen flex flex-col bg-background text-foreground transition-colors duration-200">
            <Navbar />
            <div className="flex-1 flex flex-col">
              <Suspense
                fallback={
                  <div className="flex-1 flex items-center justify-center min-h-[60vh]">
                    <LoadingIndicator />
                  </div>
                }
              >
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/graph" element={<GraphPage />} />
                  <Route path="/actors/:actorId" element={<ActorPage />} />
                  <Route path="/reports/:actorId" element={<ReportPage />} />
                  {/* Fallback unknown routes to Home */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Suspense>
            </div>
            <Footer />
            {/* Gemini Multi-turn Chatbot Drawer */}
            <GeminiChatDrawer />
          </div>
        </BrowserRouter>
      </ChatProvider>
    </ThemeProvider>
  );
}

