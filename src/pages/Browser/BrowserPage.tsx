import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  RiGlobalLine,
  RiArrowRightLine,
  RiRefreshLine,
  RiCameraLine,
  RiCursorLine,
  RiText,
  RiShieldCheckLine,
  RiTerminalBoxLine
} from 'react-icons/ri';
import { gatewayClient } from '@/lib/gateway-client';

export const BrowserPage: React.FC = () => {
  const [urlInput, setUrlInput] = useState<string>('https://news.ycombinator.com');
  const [currentUrl, setCurrentUrl] = useState<string>('about:blank');
  const [currentTitle, setCurrentTitle] = useState<string>('No Active Session');
  const [screenshotBase64, setScreenshotBase64] = useState<string>('');
  const [domSummary, setDomSummary] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [actionLog, setActionLog] = useState<string[]>([]);
  const [clickSelector, setClickSelector] = useState<string>('');
  const [typeSelector, setTypeSelector] = useState<string>('');
  const [typeText, setTypeText] = useState<string>('');

  useEffect(() => {
    fetchScreenshot();
  }, []);

  const fetchScreenshot = async () => {
    const res = await gatewayClient.invokeTool('browser_screenshot', {});
    if (res.success && res.data) {
      if (res.data.screenshot_base64) setScreenshotBase64(res.data.screenshot_base64);
      if (res.data.url) setCurrentUrl(res.data.url);
      if (res.data.title) setCurrentTitle(res.data.title);
    }
  };

  const handleNavigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!urlInput.trim() || isLoading) return;

    setIsLoading(true);
    setActionLog((prev) => [`[NAVIGATE] Requesting ${urlInput}...`, ...prev]);

    const res = await gatewayClient.invokeTool('browser_open', { url: urlInput });
    if (res.success && res.data) {
      setCurrentUrl(res.data.url);
      setCurrentTitle(res.data.title);
      setDomSummary(res.data.dom_summary || '');
      if (res.data.screenshot_base64) {
        setScreenshotBase64(res.data.screenshot_base64);
      }
      setActionLog((prev) => [`[SUCCESS] Loaded '${res.data.title}' (${res.data.status_code})`, ...prev]);
    } else {
      setActionLog((prev) => [`[ERROR] ${res.error || 'Failed to open URL'}`, ...prev]);
    }
    setIsLoading(false);
  };

  const handleClickElement = async () => {
    if (!clickSelector.trim()) return;
    setActionLog((prev) => [`[CLICK] Element '${clickSelector}'...`, ...prev]);
    const res = await gatewayClient.invokeTool('browser_click', { selector: clickSelector });
    if (res.success) {
      setActionLog((prev) => [`[SUCCESS] Dispatched click to '${clickSelector}'`, ...prev]);
      setClickSelector('');
    } else {
      setActionLog((prev) => [`[ERROR] Click blocked or failed: ${res.error}`, ...prev]);
    }
  };

  const handleTypeText = async () => {
    if (!typeSelector.trim() || !typeText.trim()) return;
    setActionLog((prev) => [`[TYPE] Writing '${typeText}' into '${typeSelector}'...`, ...prev]);
    const res = await gatewayClient.invokeTool('browser_type', { selector: typeSelector, text: typeText });
    if (res.success) {
      setActionLog((prev) => [`[SUCCESS] Typed text into '${typeSelector}'`, ...prev]);
      setTypeSelector('');
      setTypeText('');
    } else {
      setActionLog((prev) => [`[ERROR] Type action blocked or failed: ${res.error}`, ...prev]);
    }
  };

  return (
    <div className="flex h-full w-full bg-zinc-950/60 backdrop-blur-md text-zinc-100 overflow-hidden font-sans select-none">
      {/* Browser Viewport & Navigation Area */}
      <div className="flex-1 flex flex-col h-full border-r border-white/5 overflow-hidden">
        {/* Navigation URL Bar */}
        <div className="p-3 border-b border-white/5 bg-zinc-950/80 flex items-center gap-3">
          <form onSubmit={handleNavigate} className="flex-1 flex items-center gap-2">
            <div className="flex-1 relative flex items-center">
              <RiGlobalLine className="absolute left-3 text-zinc-500 text-sm" />
              <input
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="Enter URL to browse (e.g. https://github.com/NousResearch)..."
                className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-900/90 border border-white/10 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-zinc-950 text-xs font-mono font-bold transition-all shadow-[0_0_15px_rgba(16,185,129,0.25)] flex items-center gap-1.5 cursor-pointer"
            >
              {isLoading ? <RiRefreshLine className="animate-spin" /> : <RiArrowRightLine />}
              {isLoading ? 'Loading' : 'Navigate'}
            </button>
          </form>

          <button
            onClick={() => fetchScreenshot()}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 transition-all cursor-pointer"
            title="Refresh Viewport"
          >
            <RiCameraLine />
          </button>
        </div>

        {/* Viewport Canvas Preview */}
        <div className="flex-1 p-4 bg-zinc-950/40 flex flex-col items-center justify-center overflow-hidden">
          <div className="w-full h-full max-w-5xl rounded-2xl border border-white/10 bg-zinc-900/90 overflow-hidden flex flex-col shadow-2xl">
            {/* Viewport Title Bar */}
            <div className="px-4 py-2 bg-zinc-950/80 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                <span className="ml-2 text-[11px] font-mono text-zinc-400 truncate max-w-md">
                  {currentTitle}
                </span>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                <RiShieldCheckLine /> GATED SESSION
              </span>
            </div>

            {/* Viewport Image Render */}
            <div className="flex-1 flex items-center justify-center p-4 bg-zinc-950/60 overflow-hidden">
              {screenshotBase64 ? (
                <img
                  src={`data:image/svg+xml;base64,${screenshotBase64}`}
                  alt="Browser Viewport"
                  className="max-h-full max-w-full object-contain rounded-lg border border-white/5 shadow-lg"
                />
              ) : (
                <div className="text-center opacity-40">
                  <RiGlobalLine className="text-5xl mx-auto text-zinc-600 mb-2" />
                  <p className="text-xs font-mono text-zinc-400">No active browser viewport session</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Controls & DOM Inspector Drawer */}
      <div className="w-96 p-5 bg-zinc-950/80 flex flex-col justify-between overflow-y-auto space-y-6">
        <div>
          <div className="border-b border-white/5 pb-3 mb-4">
            <h3 className="text-xs font-mono font-bold tracking-wider text-emerald-400 uppercase">
              BROWSER AUTOMATION NODE
            </h3>
            <p className="text-[10px] font-mono text-zinc-500 mt-0.5">
              OpenClaw DOM element targeting & gated input actions
            </p>
          </div>

          {/* Action 1: Click Element */}
          <div className="space-y-2 mb-5">
            <span className="text-[10px] font-mono uppercase text-zinc-400 flex items-center gap-1">
              <RiCursorLine /> Click Selector (HIGH Risk)
            </span>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={clickSelector}
                onChange={(e) => setClickSelector(e.target.value)}
                placeholder="CSS selector or ID (e.g. #submit-btn)..."
                className="flex-1 px-3 py-1.5 rounded-lg bg-zinc-900 border border-white/10 text-xs text-zinc-200 focus:outline-none focus:border-amber-500/50"
              />
              <button
                onClick={handleClickElement}
                className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 text-xs font-mono font-bold transition-all cursor-pointer"
              >
                Click
              </button>
            </div>
          </div>

          {/* Action 2: Type Text */}
          <div className="space-y-2 mb-5">
            <span className="text-[10px] font-mono uppercase text-zinc-400 flex items-center gap-1">
              <RiText /> Type Text (HIGH Risk)
            </span>
            <div className="space-y-2">
              <input
                type="text"
                value={typeSelector}
                onChange={(e) => setTypeSelector(e.target.value)}
                placeholder="Target selector (e.g. input[name='search'])..."
                className="w-full px-3 py-1.5 rounded-lg bg-zinc-900 border border-white/10 text-xs text-zinc-200 focus:outline-none"
              />
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={typeText}
                  onChange={(e) => setTypeText(e.target.value)}
                  placeholder="Text to type..."
                  className="flex-1 px-3 py-1.5 rounded-lg bg-zinc-900 border border-white/10 text-xs text-zinc-200 focus:outline-none"
                />
                <button
                  onClick={handleTypeText}
                  className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 text-xs font-mono font-bold transition-all cursor-pointer"
                >
                  Type
                </button>
              </div>
            </div>
          </div>

          {/* DOM Text Summary */}
          {domSummary && (
            <div className="space-y-2 mb-5">
              <span className="text-[10px] font-mono uppercase text-zinc-400">
                DOM Text Summary
              </span>
              <div className="p-3 rounded-xl bg-zinc-900/90 border border-white/5 text-[11px] font-mono text-zinc-300 max-h-36 overflow-y-auto whitespace-pre-wrap">
                {domSummary}
              </div>
            </div>
          )}
        </div>

        {/* Action History Log */}
        <div className="space-y-2 border-t border-white/5 pt-4">
          <span className="text-[10px] font-mono uppercase text-zinc-500 flex items-center gap-1">
            <RiTerminalBoxLine /> Action History
          </span>
          <div className="p-2.5 rounded-xl bg-zinc-900/80 border border-white/5 font-mono text-[10px] text-zinc-400 max-h-32 overflow-y-auto space-y-1">
            {actionLog.length === 0 ? (
              <span className="text-zinc-600">No actions performed yet.</span>
            ) : (
              actionLog.map((log, idx) => (
                <div key={idx} className="truncate">
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BrowserPage;
