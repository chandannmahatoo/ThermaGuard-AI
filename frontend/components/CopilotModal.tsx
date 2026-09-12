'use client';
import React, { FormEvent, useEffect, useRef } from 'react';
import {
  Sparkles,
  X,
  Send,
  Shield,
  HelpCircle,
  AlertTriangle,
  Flame,
  Layers,
  MapPin,
} from 'lucide-react';
import type { ThermalEvent } from '../lib/api';

type CopilotModalProps = {
  isOpen: boolean;
  onClose: () => void;
  selected: ThermalEvent | null;
  question: string;
  setQuestion: (q: string) => void;
  answer: string;
  chatMode: string;
  chatBusy: boolean;
  onAsk: (e: FormEvent) => void;
  onSelectSuggestedQuestion: (q: string) => void;
};

export default function CopilotModal({
  isOpen,
  onClose,
  selected,
  question,
  setQuestion,
  answer,
  chatMode,
  chatBusy,
  onAsk,
  onSelectSuggestedQuestion,
}: CopilotModalProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const isGemini = chatMode === 'gemini';
  const isFallback = chatMode === 'deterministic_fallback';

  const suggestions = selected
    ? [
        `Why is event ${selected.id.slice(0, 12)}… marked ${selected.risk?.risk_level || 'this risk'}?`,
        'What thermal and atmospheric measurements were observed?',
        'Is there nearby industrial infrastructure or OSM context?',
        'Summarize satellite sensor sources and cross-confirmation.',
      ]
    : [
        'Summarize the highest risk thermal anomalies currently monitored.',
        'Which events have cross-sensor satellite confirmation?',
        'What industrial activity is detected near active hotspots?',
        'Explain how the deterministic risk engine scores events.',
      ];

  return (
    <div className="copilot-backdrop" onClick={onClose}>
      <div
        className="copilot-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="ThermaGuard AI Copilot"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="copilot-header">
          <div className="copilot-header-brand">
            <div className="copilot-icon-pill">
              <Sparkles size={18} />
            </div>
            <div>
              <h2>ThermaGuard AI Copilot</h2>
              <span className="copilot-subtext">
                {selected
                  ? `Target: Event ${selected.id.slice(0, 16)}… (${selected.risk?.risk_level || 'Risk'} · ${selected.mean_frp?.toFixed(1) || '0'} MW)`
                  : 'Scope: Top active thermal anomalies in workspace'}
              </span>
            </div>
          </div>

          <div className="copilot-header-actions">
            {chatMode && (
              <span className={`copilot-provider-badge ${isGemini ? 'badge-gemini' : 'badge-fallback'}`}>
                {isGemini ? '✦ Powered by Gemini API' : '⚡ Deterministic Fallback'}
              </span>
            )}
            <button
              type="button"
              className="copilot-close-btn"
              onClick={onClose}
              aria-label="Close copilot"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Selected event context chip if applicable */}
        {selected && (
          <div className="copilot-event-context-bar">
            <MapPin size={13} />
            <span>
              <b>Selected Event:</b> {selected.context?.location?.display_name || `${selected.latitude.toFixed(3)}°, ${selected.longitude.toFixed(3)}°`} · Score: <b>{selected.risk?.risk_score}/100</b>
            </span>
          </div>
        )}

        {/* Safety & Grounding Notice */}
        <div className="copilot-grounding-notice">
          <Shield size={14} className="text-teal" />
          <span>
            <b>Evidence Grounded:</b> Copilot only explains verified satellite and contextual evidence. It cannot alter database records, overwrite RandomForest classification, or adjust risk scores.
          </span>
        </div>

        {/* Answer Display Area */}
        <div className="copilot-conversation-area">
          {chatBusy ? (
            <div className="copilot-busy-state">
              <Sparkles size={22} className="spin text-teal" />
              <p>Grounding query against verified event evidence…</p>
            </div>
          ) : answer ? (
            <div className="copilot-answer-rendered">
              <div className="copilot-answer-bubble">{answer}</div>
              {isFallback && (
                <div className="copilot-fallback-banner">
                  <AlertTriangle size={13} />
                  <span>Gemini unavailable — deterministic evidence summary</span>
                </div>
              )}
            </div>
          ) : (
            <div className="copilot-placeholder-state">
              <Sparkles size={32} className="text-muted" />
              <p>
                Ask questions about risk drivers, ML classification, satellite observations, or atmospheric context.
              </p>
            </div>
          )}
        </div>

        {/* Prompt Suggestions */}
        <div className="copilot-suggestions-bar">
          <span className="suggestions-label">Suggested prompts:</span>
          <div className="suggestions-chips">
            {suggestions.map((s, idx) => (
              <button
                key={idx}
                type="button"
                className="suggestion-chip"
                onClick={() => onSelectSuggestedQuestion(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form */}
        <form className="copilot-input-form" onSubmit={onAsk}>
          <input
            ref={inputRef}
            type="text"
            aria-label="Copilot question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              selected
                ? `Ask about event ${selected.id.slice(0, 8)}…`
                : 'Ask about thermal risk across monitored events…'
            }
            required
            maxLength={1000}
            disabled={chatBusy}
          />
          <button
            type="submit"
            className="primary copilot-send-button"
            disabled={chatBusy || !question.trim()}
            aria-label="Send query to copilot"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
