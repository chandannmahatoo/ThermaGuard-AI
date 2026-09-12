'use client';
import React from 'react';
import {
  Database,
  RefreshCw,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Layers,
  FileCheck,
  GitBranch,
} from 'lucide-react';
import type { ModelStatus } from '../lib/api';
import { StatusBadge } from './StatusBadge';

type ReviewCenterProps = {
  model: ModelStatus | null;
  candidates?: {event_id:string;reviewed:string;label:string}[] | null;
  readiness?: {reviewed_rows:number;eligible_rows:number;classes_present:number;classes_total:number;split_groups:number;training_ready:boolean;missing:string[];problems:string[]} | null;
  isAdmin: boolean;
  trainBusy: boolean;
  onTrainModel: () => void;
};

export default function ReviewCenter({
  model,
  readiness,
  candidates,
  isAdmin,
  trainBusy,
  onTrainModel,
}: ReviewCenterProps) {
  const isAvailable = model?.model_available === true;
  const isReady = model?.training_ready === true;
  const eligibleRows = model?.eligible_labeled_rows ?? 0;
  const targetRows = 30;
  const progressPct = Math.min(100, Math.round((eligibleRows / targetRows) * 100));

  return (
    <div className="review-center-container">
      {/* Header */}
      <div className="review-center-header">
        <div>
          <h2>Classification Model &amp; Human Review Gating</h2>
          <p className="text-muted">
            The machine learning classification is an explainable RandomForest model trained strictly on reviewed observations.
            RandomForest is the classification source-of-truth, while the deterministic risk engine remains the authoritative risk source-of-truth.
          </p>
        </div>
      </div>

      <section className="review-card"><h3>Human review readiness</h3>{readiness ? <><dl className="review-meta-dl"><div><dt>Reviewed rows</dt><dd>{readiness.reviewed_rows}</dd></div><div><dt>Eligible rows</dt><dd>{readiness.eligible_rows}</dd></div><div><dt>Classes represented</dt><dd>{readiness.classes_present} / {readiness.classes_total}</dd></div><div><dt>Independent split groups</dt><dd>{readiness.split_groups}</dd></div></dl>{[...(readiness.missing || []), ...(readiness.problems || [])].map((reason,i)=><p key={i}>{reason}</p>)}</> : <p>Review readiness unavailable.</p>}<p>V2-specific readiness is not exposed by this response. Candidate details are available to administrators only. Review labels remain a human, offline workflow; independent split groups prevent leakage.</p></section>{candidates && <section className="review-card"><h3>Candidate label distribution</h3><p>{candidates.length} candidates · {candidates.filter(c=>c.reviewed.toLowerCase()!=='true').length} pending review</p><dl>{Object.entries(candidates.reduce<Record<string,number>>((counts,c)=>{const key=c.label || 'Unlabeled';counts[key]=(counts[key]||0)+1;return counts},{})).map(([label,count])=><div key={label}><dt>{label.replaceAll('_',' ')}</dt><dd>{count}</dd></div>)}</dl><p>Candidate review claims are snapshots. Eligibility and current event evidence must be validated before finalizing labels.</p></section>}<div className="review-grid">
        {/* Model Status Card */}
        <section className="review-card">
          <div className="review-card-top">
            <div className="review-card-icon">
              <Database size={20} className="text-teal" />
            </div>
            <div>
              <h3>RandomForest Classifier</h3>
              <span className="text-muted small">Decision Support Engine</span>
            </div>
            <div className="review-card-badge">
              <StatusBadge state={isAvailable ? 'REAL' : 'UNAVAILABLE'} />
            </div>
          </div>

          <p className="review-card-desc">
            {isAvailable
              ? 'Trained MVP classifier operating on reviewed ground truth candidate observations. Decision-support classifier.'
              : model?.reason || 'Classifier model not trained yet. Human review labels are required.'}
          </p>

          <dl className="review-meta-dl">
            <div>
              <dt>Model Version</dt>
              <dd>{model?.model_version || 'Not trained'}</dd>
            </div>
            <div>
              <dt>Feature Version</dt>
              <dd>{model?.feature_version || 'Unavailable'}</dd>
            </div>
            <div>
              <dt>Training Gate Ready</dt>
              <dd>
                {isReady ? (
                  <span className="text-green font-semibold">Yes (Eligible)</span>
                ) : (
                  <span className="text-amber">Pending labels</span>
                )}
              </dd>
            </div>
            <div>
              <dt>Eligible Labeled Rows</dt>
              <dd><b>{eligibleRows}</b> / {targetRows}</dd>
            </div>
          </dl>

          {/* Progress towards training gate */}
          <div className="training-gate-progress-box">
            <div className="gate-progress-header">
              <span>Training Gate Progress</span>
              <b>{progressPct}% ({eligibleRows}/{targetRows} rows)</b>
            </div>
            <div className="gate-progress-track">
              <div className="gate-progress-bar" style={{ width: `${progressPct}%` }} />
            </div>
            <p className="small text-muted">
              Training gate requires at least 30 reviewed rows covering all 5 classes with 10 split groups.
            </p>
          </div>

          {isAdmin && (
            <div className="review-admin-actions">
              <button
                type="button"
                className="button review-train-btn"
                disabled={!isReady || trainBusy}
                onClick={onTrainModel}
              >
                <RefreshCw size={15} className={trainBusy ? 'spin' : ''} />
                {trainBusy ? 'Training Model…' : 'Train Reviewed Dataset'}
              </button>
              {!isReady && (
                <p className="small text-muted">
                  Training requires the reviewed-label gate (30+ rows, all five classes, 10 split groups). Label candidates via the review workflow — do not force it.
                </p>
              )}
            </div>
          )}
        </section>

        {/* System Architecture & Principles Card */}
        <section className="review-card">
          <div className="review-card-top">
            <div className="review-card-icon">
              <ShieldCheck size={20} className="text-teal" />
            </div>
            <div>
              <h3>Architectural Safeguards</h3>
              <span className="text-muted small">Evidence &amp; Traceability Rules</span>
            </div>
          </div>

          <ul className="safeguards-list">
            <li>
              <CheckCircle2 size={16} className="text-green" />
              <div>
                <b>RandomForest is Source-of-Truth</b>
                <p className="small text-muted">
                  Classifies thermal events using the backend model taxonomy displayed in the candidate distribution. Gemini never overrides this.
                </p>
              </div>
            </li>
            <li>
              <CheckCircle2 size={16} className="text-green" />
              <div>
                <b>Deterministic Risk Engine</b>
                <p className="small text-muted">
                  Authoritative risk score (0–100) calculated from thermal severity, persistence, proximity, and deviations.
                </p>
              </div>
            </li>
            <li>
              <CheckCircle2 size={16} className="text-green" />
              <div>
                <b>Gemini for Explanation Only</b>
                <p className="small text-muted">
                  Gemini generates plain-language explanations of supplied evidence and never fabricates casualties, causes, or weather.
                </p>
              </div>
            </li>
            <li>
              <CheckCircle2 size={16} className="text-green" />
              <div>
                <b>Immutable Event Data</b>
                <p className="small text-muted">
                  Copilot requests do not modify, mutate, or re-weight database event records or reviewed labels.
                </p>
              </div>
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
