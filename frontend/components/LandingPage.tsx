'use client';
import React from 'react';
import {
  Flame,
  ScanLine,
  Layers,
  Activity,
  Shield,
  Sparkles,
  MapPin,
  Bell,
  ArrowRight,
  ShieldCheck,
  Radio,
  CheckCircle2,
  Wind,
  Globe,
  Route,
  Database,
  Lock,
} from 'lucide-react';

type LandingPageProps = {
  onSignIn: () => void;
  onSignUp: () => void;
  demoMode: boolean;
};

export default function LandingPage({ onSignIn, onSignUp, demoMode }: LandingPageProps) {
  return (
    <div className="landing-wrapper">
      {/* Top Navigation */}
      <header className="landing-header">
        <div className="landing-nav-container">
          <div className="brand">
            <span className="brand-mark">
              <Flame size={20} />
            </span>
            <span>
              ThermaGuard <b>AI</b>
              <small>GEOSPATIAL INTELLIGENCE</small>
            </span>
          </div>

          <nav className="landing-nav-links">
            <a href="#capabilities">Capabilities</a>
            <a href="#architecture">Architecture</a>
            <a href="#safeguards">Safeguards</a>
          </nav>

          <div className="landing-nav-actions">
            {demoMode && <span className="demo-tag">DEMO BENCHMARK</span>}
            <button
              type="button"
              className="button landing-signin-btn"
              onClick={onSignIn}
            >
              Sign In
            </button>
            <button
              type="button"
              className="primary landing-cta-btn"
              onClick={onSignUp}
            >
              Request Access
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="landing-hero-content">
          <div className="landing-hero-badge">
            <span className="hero-badge-dot" />
            <span>SMART INDIA HACKATHON 2026 · AI &amp; GEOSPATIAL SURVEILLANCE</span>
          </div>

          <h1 className="landing-hero-title">
            AI-Powered Geospatial
            <br />
            Thermal Intelligence
          </h1>

          <p className="landing-hero-subtitle">
            Near-real-time satellite thermal anomaly monitoring with contextual geospatial intelligence, event classification, deterministic risk assessment, and evidence-grounded AI assistance.
          </p>

          <div className="landing-hero-actions">
            <button
              type="button"
              className="primary hero-primary-cta"
              onClick={onSignIn}
            >
              Sign In to Operations Console
              <ArrowRight size={16} />
            </button>
            <button
              type="button"
              className="button hero-secondary-cta"
              onClick={onSignUp}
            >
              Create Account / Request Access
            </button>
          </div>

          {/* Quick Technical Specs Strip */}
          <div className="landing-specs-strip">
            <div className="spec-item">
              <span className="spec-val">VIIRS &amp; MODIS</span>
              <span className="spec-label">NASA FIRMS Satellites</span>
            </div>
            <div className="spec-item">
              <span className="spec-val">Provider APIs</span>
              <span className="spec-label">Configuration dependent</span>
            </div>
            <div className="spec-item">
              <span className="spec-val">RandomForest</span>
              <span className="spec-label">5-Class ML Classification</span>
            </div>
            <div className="spec-item">
              <span className="spec-val">0–100 Score</span>
              <span className="spec-label">Deterministic Risk Engine</span>
            </div>
          </div>
        </div>
      </section>

      {/* Capabilities Section */}
      <section id="capabilities" className="landing-section">
        <div className="section-title-wrap">
          <span className="eyebrow">INTEGRATED PIPELINE</span>
          <h2>Comprehensive Environmental Intelligence</h2>
          <p className="text-muted">
            ThermaGuard AI connects spaceborne Earth observation data with local environmental, industrial, and atmospheric context.
          </p>
        </div>

        <div className="landing-features-grid">
          {/* Card 1: FIRMS */}
          <div className="feature-card">
            <div className="feature-icon-wrap icon-cyan">
              <Flame size={20} />
            </div>
            <h3>NASA FIRMS Hotspot Detection</h3>
            <p>
              Direct ingestion and source-aware normalization of active fire detections from VIIRS (375m) and MODIS (1km) sensors.
            </p>
            <span className="feature-pill">Near-Real-Time Feed</span>
          </div>

          {/* Card 2: Industrial Context */}
          <div className="feature-card">
            <div className="feature-icon-wrap icon-amber">
              <Activity size={20} />
            </div>
            <h3>Industrial Context (OSM)</h3>
            <p>
              Identifies nearby industrial complexes, refineries, flare stacks, and residential borders within 5 km to separate controlled activity from wildfires.
            </p>
            <span className="feature-pill">Overpass Intelligence</span>
          </div>

          {/* Card 3: Satellite NDVI */}
          <div className="feature-card">
            <div className="feature-icon-wrap icon-teal">
              <Radio size={20} />
            </div>
            <h3>Copernicus Sentinel-2</h3>
            <p>
              Surface reflectance vegetation indexing (NDVI) and land-use classifications provide ground cover verification for observed thermal footprints.
            </p>
            <span className="feature-pill">Sentinel-2 L2A</span>
          </div>

          {/* Card 4: Atmospheric Context */}
          <div className="feature-card">
            <div className="feature-icon-wrap icon-green">
              <Wind size={20} />
            </div>
            <h3>Weather &amp; Air Quality</h3>
            <p>
              Modelled hourly grid atmospheric data from Open-Meteo tracking surface temperature, wind vectors, PM2.5, PM10, and CO dispersion.
            </p>
            <span className="feature-pill">Open-Meteo Grid</span>
          </div>

          {/* Card 5: EONET Hazard Correlation */}
          <div className="feature-card">
            <div className="feature-icon-wrap icon-purple">
              <Globe size={20} />
            </div>
            <h3>NASA EONET Natural Hazards</h3>
            <p>
              Correlates thermal anomalies with active volcanic eruptions, wildfires, and severe storm events published by NASA Earth Observatory.
            </p>
            <span className="feature-pill">NASA EONET API</span>
          </div>

          {/* Card 6: AI Copilot */}
          <div className="feature-card">
            <div className="feature-icon-wrap icon-indigo">
              <Sparkles size={20} />
            </div>
            <h3>Evidence-Grounded AI Copilot</h3>
            <p>
              Google Gemini API answers operational queries using ONLY verified event facts. Fully backed by a deterministic fallback when offline.
            </p>
            <span className="feature-pill">Gemini &amp; Fallback</span>
          </div>

          {/* Card 7: Location-Aware Alerting */}
          <div className="feature-card">
            <div className="feature-icon-wrap icon-red">
              <Bell size={20} />
            </div>
            <h3>Automated Dispatch &amp; Alerts</h3>
            <p>
              Deterministic threshold alerting dispatching SMTP emails and Firebase push notifications to organizations within subscriber radius.
            </p>
            <span className="feature-pill">SMTP &amp; Firebase</span>
          </div>

          {/* Card 8: Emergency Routing */}
          <div className="feature-card">
            <div className="feature-icon-wrap icon-blue">
              <Route size={20} />
            </div>
            <h3>Emergency Road Access</h3>
            <p>
              OpenRouteService logistics calculating driving routes, distance in meters, and travel duration from road networks to event coordinates.
            </p>
            <span className="feature-pill">OpenRouteService</span>
          </div>
        </div>
      </section>

      {/* Architecture & Safeguards Section */}
      <section id="architecture" className="landing-section landing-section-alt">
        <div className="section-title-wrap">
          <span className="eyebrow">DESIGN INTEGRITY</span>
          <h2>Architectural Reliability &amp; Safeguards</h2>
          <p className="text-muted">
            Decision support built with strict boundaries to constrain machine learning and AI explanations or compromise operational ground truth.
          </p>
        </div>

        <div className="architecture-flow-box">
          <div className="flow-step">
            <div className="flow-badge">1</div>
            <h4>NASA FIRMS</h4>
            <p className="small">Satellite Hotspot Ingestion</p>
          </div>
          <div className="flow-divider">→</div>
          <div className="flow-step">
            <div className="flow-badge">2</div>
            <h4>Clustering</h4>
            <p className="small">Spatial-Temporal Aggregation</p>
          </div>
          <div className="flow-divider">→</div>
          <div className="flow-step">
            <div className="flow-badge">3</div>
            <h4>Enrichment</h4>
            <p className="small">OSM, Weather &amp; Satellite</p>
          </div>
          <div className="flow-divider">→</div>
          <div className="flow-step">
            <div className="flow-badge">4</div>
            <h4>RandomForest</h4>
            <p className="small">Classification Source-of-Truth</p>
          </div>
          <div className="flow-divider">→</div>
          <div className="flow-step">
            <div className="flow-badge">5</div>
            <h4>Risk Engine</h4>
            <p className="small">Authoritative 0–100 Score</p>
          </div>
          <div className="flow-divider">→</div>
          <div className="flow-step">
            <div className="flow-badge">6</div>
            <h4>Alerts &amp; Copilot</h4>
            <p className="small">Dispatch &amp; Explanation</p>
          </div>
        </div>

        <div id="safeguards" className="safeguards-card-grid">
          <div className="safeguard-item">
            <CheckCircle2 size={18} className="text-teal" />
            <div>
              <b>RandomForest Classification is Authoritative</b>
              <p className="small text-muted">
                Trained on human-reviewed ground truth observations. Gemini never reclassifies events or overrides model output.
              </p>
            </div>
          </div>

          <div className="safeguard-item">
            <CheckCircle2 size={18} className="text-teal" />
            <div>
              <b>Deterministic Risk Calculation</b>
              <p className="small text-muted">
                Mathematical formula based on fire radiative power, persistence, proximity, and historical baselines.
              </p>
            </div>
          </div>

          <div className="safeguard-item">
            <CheckCircle2 size={18} className="text-teal" />
            <div>
              <b>Immutable Database Records</b>
              <p className="small text-muted">
                Copilot queries operate in read-only mode over single-event evidence packets without write reservations.
              </p>
            </div>
          </div>

          <div className="safeguard-item">
            <CheckCircle2 size={18} className="text-teal" />
            <div>
              <b>Deterministic Offline Fallback</b>
              <p className="small text-muted">
                If Gemini API is unreachable or rate-limited, system returns a factual evidence summary without failure.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action Banner */}
      <section className="landing-cta-banner">
        <h2>Ready to access the monitoring console?</h2>
        <p className="text-muted">
          Authenticate with your operational credentials or request organization assignment from your system administrator.
        </p>
        <div className="landing-cta-buttons">
          <button
            type="button"
            className="primary cta-large-btn"
            onClick={onSignIn}
          >
            Sign In to Console
            <ArrowRight size={16} />
          </button>
          <button
            type="button"
            className="button cta-large-btn"
            onClick={onSignUp}
          >
            Create Account / Request Access
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-footer-container">
          <div className="brand">
            <span className="brand-mark">
              <Flame size={18} />
            </span>
            <span>
              ThermaGuard <b>AI</b>
            </span>
          </div>
          <p className="small text-muted">
            Smart India Hackathon 2026 · Problem Statement: Satellite-Derived Thermal Anomaly Detection &amp; Risk Intelligence.
          </p>
          <div className="footer-links">
            <button type="button" onClick={onSignIn}>Sign In</button>
            <button type="button" onClick={onSignUp}>Register</button>
          </div>
        </div>
      </footer>
    </div>
  );
}
