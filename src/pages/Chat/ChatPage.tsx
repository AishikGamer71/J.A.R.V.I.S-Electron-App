import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RiSendPlane2Fill,
  RiSearchLine,
  RiAddLine,
  RiCpuLine,
  RiCloudLine,
  RiFlashlightLine,
  RiShieldCheckLine,
  RiAlertLine,
  RiCheckDoubleLine,
  RiDeleteBinLine
} from 'react-icons/ri';
import { gatewayClient, ChatMessage } from '@/lib/gateway-client';

interface ChatPageProps {
  onNavigateHome?: () => void;
}

export const ChatPage: React.FC<ChatPageProps> = () => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ChatMessage[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [activeRouteInfo, setActiveRouteInfo] = useState<{
    tier: string;
    model: string;
    isFallback: boolean;
    reason: string;
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadSessions();
    const unsubRoute = gatewayClient.onChatRouted((data) => {
      setActiveRouteInfo({
        tier: data.tier,
        model: data.model,
        isFallback: data.isFallback,
        reason: data.reason
      });
    });
    return () => {
      unsubRoute();
    };
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
    }
  }, [activeSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const loadSessions = async () => {
    const list = await gatewayClient.getSessions();
    setSessions(list);
    if (list.length > 0 && !activeSessionId) {
      setActiveSessionId(list[0].id);
    } else if (list.length === 0 && !activeSessionId) {
      createNewSession();
    }
  };

  const loadMessages = async (sessionId: string) => {
    const msgs = await gatewayClient.getMessages(sessionId);
    setMessages(msgs);
  };

  const createNewSession = () => {
    const newId = 'session_' + Date.now();
    setActiveSessionId(newId);
    setMessages([]);
    setActiveRouteInfo(null);
  };

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (!q.trim()) {
      setIsSearching(false);
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    const res = await gatewayClient.searchMessages(q);
    setSearchResults(res);
  };

  const handleSendMessage = () => {
    if (!inputMessage.trim() || isStreaming) return;
    const userText = inputMessage;
    setInputMessage('');

    const tempUserMsg: ChatMessage = {
      id: 'temp_u_' + Date.now(),
      session_id: activeSessionId,
      role: 'user',
      content: userText,
      created_at: Date.now() / 1000
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsStreaming(true);
    setStreamingContent('');

    gatewayClient.sendChat(
      activeSessionId,
      userText,
      (delta) => {
        setStreamingContent((prev) => prev + delta);
      },
      (completedMsg) => {
        setStreamingContent('');
        setIsStreaming(false);
        setMessages((prev) => [...prev, completedMsg]);
        loadSessions();
      },
      (err) => {
        console.error('Chat error:', err);
        setIsStreaming(false);
        const errorMsg: ChatMessage = {
          id: 'temp_err_' + Date.now(),
          session_id: activeSessionId,
          role: 'assistant',
          content: '⚠️ Unable to complete request: ' + (err.message || String(err)),
          created_at: Date.now() / 1000
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    );
  };

  const renderTierBadge = (tier?: string, model?: string) => {
    if (!tier) return null;
    let label = 'Tier 1 Local';
    let icon = <RiCpuLine className="text-emerald-400" />;
    let colorClass = 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20';

    if (tier === 'tier2_balanced') {
      label = 'Tier 2 Balanced';
      icon = <RiFlashlightLine className="text-cyan-400" />;
      colorClass = 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20';
    } else if (tier === 'tier3_cloud') {
      label = 'Tier 3 Cloud';
      icon = <RiCloudLine className="text-indigo-400" />;
      colorClass = 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20';
    }

    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono font-medium rounded-full border ${colorClass}`}
      >
        {icon} {label} {model ? `(${model.split('/').pop()})` : ''}
      </span>
    );
  };

  return (
    <div className="flex h-full w-full bg-zinc-950/60 backdrop-blur-md text-zinc-100 overflow-hidden font-sans">
      {/* Sessions & Search Sidebar */}
      <div className="w-72 border-r border-white/5 flex flex-col bg-zinc-950/40 select-none">
        <div className="p-3 border-b border-white/5 flex items-center justify-between">
          <span className="text-xs font-mono font-semibold tracking-wider text-emerald-400 flex items-center gap-1.5">
            <RiShieldCheckLine /> SESSIONS & ARCHIVE
          </span>
          <button
            onClick={createNewSession}
            className="p-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 transition-all text-xs flex items-center gap-1 cursor-pointer"
          >
            <RiAddLine className="text-sm" /> New
          </button>
        </div>

        {/* FTS5 Search Input */}
        <div className="p-3 border-b border-white/5">
          <div className="relative">
            <RiSearchLine className="absolute left-2.5 top-2.5 text-zinc-500 text-sm" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search history (FTS5)..."
              className="w-full pl-8 pr-3 py-1.5 bg-zinc-900/60 border border-white/10 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50"
            />
          </div>
        </div>

        {/* List of Sessions or Search Results */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isSearching ? (
            <div>
              <div className="px-2 py-1 text-[10px] font-mono text-zinc-500 uppercase">
                Search Results ({searchResults.length})
              </div>
              {searchResults.map((res) => (
                <button
                  key={res.id}
                  onClick={() => {
                    setActiveSessionId(res.session_id);
                    setIsSearching(false);
                    setSearchQuery('');
                  }}
                  className="w-full text-left p-2.5 rounded-lg bg-zinc-900/40 hover:bg-white/5 border border-white/5 transition-all text-xs"
                >
                  <div className="text-[11px] text-zinc-400 truncate">{res.content}</div>
                  <div className="text-[9px] font-mono text-zinc-600 mt-1">
                    {new Date(res.created_at * 1000).toLocaleTimeString()}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                className={`w-full text-left p-2.5 rounded-lg transition-all text-xs flex items-center justify-between group ${
                  activeSessionId === s.id
                    ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300'
                    : 'text-zinc-400 hover:bg-white/5 border border-transparent'
                }`}
              >
                <div className="truncate font-medium flex-1 mr-2">{s.title || 'Untitled Session'}</div>
                <div className="text-[9px] font-mono opacity-50">
                  {new Date(s.updated_at * 1000).toLocaleDateString()}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Conversation Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Active Route & Fallback Banner */}
        {activeRouteInfo && (
          <div className="px-4 py-2 bg-zinc-900/40 border-b border-white/5 flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              {renderTierBadge(activeRouteInfo.tier, activeRouteInfo.model)}
              {activeRouteInfo.isFallback && (
                <span className="flex items-center gap-1 text-[11px] text-amber-400 font-mono bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/20">
                  <RiAlertLine /> {activeRouteInfo.reason}
                </span>
              )}
            </div>
            <div className="text-[10px] font-mono text-zinc-500">
              JARVIS NEURAL ROUTER ACTIVE
            </div>
          </div>
        )}

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && !isStreaming && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-70">
              <RiCpuLine className="text-5xl text-emerald-500 mb-3 animate-pulse" />
              <h3 className="text-base font-bold tracking-wide text-zinc-200">
                J.A.R.V.I.S Autonomous Core Ready
              </h3>
              <p className="text-xs text-zinc-400 max-w-sm mt-1">
                Multi-tier dynamic routing active. Tier 1 commands run locally via Ollama, while complex reasoning scales to cloud models.
              </p>
              <div className="flex gap-2 mt-4">
                {['System Status', 'What are active agents?', 'Run diagnostic'].map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => {
                      setInputMessage(prompt);
                    }}
                    className="px-3 py-1.5 bg-white/5 hover:bg-emerald-500/10 border border-white/10 rounded-full text-xs text-zinc-300 transition-all cursor-pointer"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              key={msg.id}
              className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[78%] rounded-2xl p-4 text-xs leading-relaxed shadow-lg ${
                  msg.role === 'user'
                    ? 'bg-emerald-500/20 text-emerald-100 border border-emerald-500/30'
                    : 'bg-zinc-900/80 text-zinc-200 border border-white/10'
                }`}
              >
                {msg.role === 'assistant' && msg.tier && (
                  <div className="mb-2 flex items-center gap-2">
                    {renderTierBadge(msg.tier, msg.model)}
                  </div>
                )}
                <div className="whitespace-pre-wrap font-sans">{msg.content}</div>
              </div>
              <div className="text-[9px] font-mono text-zinc-500 mt-1 px-1 flex items-center gap-1">
                {msg.role === 'user' ? 'You' : 'JARVIS'} •{' '}
                {new Date(msg.created_at * 1000).toLocaleTimeString()}
              </div>
            </motion.div>
          ))}

          {/* Real-time Streaming Response Delta */}
          {isStreaming && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-start"
            >
              <div className="max-w-[78%] rounded-2xl p-4 text-xs leading-relaxed bg-zinc-900/80 text-zinc-200 border border-emerald-500/30 shadow-lg">
                <div className="mb-2 flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono font-medium rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping mr-1" />
                    Generating...
                  </span>
                </div>
                <div className="whitespace-pre-wrap font-sans">
                  {streamingContent}
                  <span className="inline-block w-1.5 h-3.5 bg-emerald-400 ml-1 animate-pulse" />
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-white/5 bg-zinc-950/60">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2 bg-zinc-900/80 border border-white/10 rounded-xl px-4 py-2 focus-within:border-emerald-500/50 transition-all shadow-xl"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask JARVIS anything or issue a system command..."
              className="flex-1 bg-transparent text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none"
              disabled={isStreaming}
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isStreaming}
              className={`p-2 rounded-lg transition-all cursor-pointer ${
                inputMessage.trim() && !isStreaming
                  ? 'bg-emerald-500 text-zinc-950 hover:bg-emerald-400'
                  : 'bg-white/5 text-zinc-600'
              }`}
            >
              <RiSendPlane2Fill className="text-sm" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
