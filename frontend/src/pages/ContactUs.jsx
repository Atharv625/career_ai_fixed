export default function ContactPage() {
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Syne:wght@700;800&display=swap');

        :root {
          --signal: #4FFFB0;
          --signal-muted: rgba(79,255,176,0.08);
          --ink-900: #0B0F1A;
          --ink-800: #111827;
          --ink-700: #1A2235;
          --ink-600: #1F2937;
          --text-primary: #E8ECF4;
          --text-muted: #6B7280;
          --text-dim: #374151;
          --purple: #A78BFA;
          --purple-muted: rgba(167,139,250,0.15);
        }

        .contact-page {
          background: var(--ink-900);
          color: var(--text-primary);
          font-family: 'DM Sans', sans-serif;
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow-x: hidden;
          padding: 24px 16px;
          position: relative;
        }

        .contact-page::before {
          content: '';
          position: fixed;
          inset: 0;
          background:
            radial-gradient(ellipse 60% 40% at 10% 20%, rgba(79,255,176,0.05) 0%, transparent 70%),
            radial-gradient(ellipse 50% 50% at 90% 80%, rgba(167,139,250,0.06) 0%, transparent 70%);
          pointer-events: none;
          z-index: 0;
        }

        .contact-container {
          position: relative;
          z-index: 1;
          width: 100%;
          max-width: 780px;
        }

        .contact-header {
          text-align: center;
          margin-bottom: 48px;
          animation: contactSlideUp 0.6s ease both;
        }

        .contact-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 999px;
          background: var(--signal-muted);
          border: 1px solid rgba(79,255,176,0.2);
          font-size: 11px;
          color: var(--signal);
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          margin-bottom: 20px;
        }

        .contact-badge-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--signal);
          animation: contactPulse 2s infinite;
        }

        .contact-h1 {
          font-family: 'Syne', sans-serif;
          font-size: clamp(2rem, 5vw, 3rem);
          font-weight: 800;
          color: #fff;
          line-height: 1.1;
          margin-bottom: 14px;
        }

        .contact-h1 span {
          background: linear-gradient(135deg, var(--signal) 0%, #00D4FF 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .contact-subtitle {
          color: var(--text-muted);
          font-size: 15px;
          max-width: 420px;
          margin: 0 auto;
          line-height: 1.6;
        }

        .contact-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }

        .contact-card {
          background: var(--ink-800);
          border-radius: 20px;
          padding: 32px 28px;
          position: relative;
          overflow: hidden;
          transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
          animation: contactSlideUp 0.6s ease both;
          cursor: default;
        }

        .contact-card.green {
          border: 1px solid rgba(79,255,176,0.08);
          animation-delay: 0.1s;
        }

        .contact-card.purple {
          border: 1px solid rgba(79,255,176,0.08);
          animation-delay: 0.2s;
        }

        .contact-card::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: 20px;
          opacity: 0;
          transition: opacity 0.3s;
          pointer-events: none;
        }

        .contact-card.green::before {
          background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(79,255,176,0.06) 0%, transparent 70%);
        }

        .contact-card.purple::before {
          background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(167,139,250,0.07) 0%, transparent 70%);
        }

        .contact-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }

        .contact-card.green:hover { border-color: rgba(79,255,176,0.25); }
        .contact-card.purple:hover { border-color: rgba(167,139,250,0.25); }
        .contact-card:hover::before { opacity: 1; }

        .contact-icon-wrap {
          width: 52px;
          height: 52px;
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 20px;
          font-size: 22px;
          position: relative;
          z-index: 1;
        }

        .contact-icon-wrap.green {
          background: var(--signal-muted);
          border: 1px solid rgba(79,255,176,0.2);
        }

        .contact-icon-wrap.purple {
          background: var(--purple-muted);
          border: 1px solid rgba(167,139,250,0.2);
        }

        .contact-card-label {
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          margin-bottom: 10px;
          position: relative;
          z-index: 1;
        }

        .contact-card-label.green { color: var(--signal); }
        .contact-card-label.purple { color: var(--purple); }

        .contact-card-title {
          font-family: 'Syne', sans-serif;
          font-size: 13px;
          font-weight: 700;
          color: var(--text-muted);
          margin-bottom: 6px;
          position: relative;
          z-index: 1;
        }

        .contact-card-value {
          font-size: 18px;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 18px;
          position: relative;
          z-index: 1;
          word-break: break-all;
        }

        .contact-card-desc {
          font-size: 13px;
          color: var(--text-muted);
          line-height: 1.6;
          margin-bottom: 24px;
          position: relative;
          z-index: 1;
        }

        .contact-card-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 20px;
          border-radius: 12px;
          font-size: 13px;
          font-weight: 600;
          text-decoration: none;
          border: none;
          cursor: pointer;
          transition: all 0.2s ease;
          position: relative;
          z-index: 1;
          font-family: 'DM Sans', sans-serif;
        }

        .contact-card-btn.green {
          background: var(--signal-muted);
          border: 1px solid rgba(79,255,176,0.2);
          color: var(--signal);
        }

        .contact-card-btn.green:hover {
          background: rgba(79,255,176,0.15);
          transform: translateX(2px);
        }

        .contact-card-btn.purple {
          background: var(--purple-muted);
          border: 1px solid rgba(167,139,250,0.2);
          color: var(--purple);
        }

        .contact-card-btn.purple:hover {
          background: rgba(167,139,250,0.2);
          transform: translateX(2px);
        }

        .contact-info-bar {
          background: var(--ink-800);
          border: 1px solid rgba(79,255,176,0.07);
          border-radius: 16px;
          padding: 20px 28px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          flex-wrap: wrap;
          animation: contactSlideUp 0.6s 0.35s ease both;
        }

        .contact-info-bar-left {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .contact-status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--signal);
          animation: contactPulse 2s infinite;
          flex-shrink: 0;
        }

        .contact-info-bar-text {
          font-size: 13px;
          color: var(--text-muted);
          line-height: 1.5;
        }

        .contact-info-bar-text strong {
          color: var(--text-primary);
          font-weight: 600;
        }

        .contact-hours-tag {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 8px;
          background: var(--signal-muted);
          border: 1px solid rgba(79,255,176,0.15);
          font-size: 12px;
          color: var(--signal);
          font-weight: 600;
          white-space: nowrap;
        }

        @keyframes contactSlideUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        @keyframes contactPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.5; transform: scale(0.85); }
        }
      `}</style>

      <div className="contact-page">
        <div className="contact-container">
          {/* Header */}
          <div className="contact-header">
            <div className="contact-badge">
              <span className="contact-badge-dot" />
              We're online
            </div>
            <h1 className="contact-h1">
              Get in <span>Touch</span>
            </h1>
            <p className="contact-subtitle">
              Have questions about your career journey? We're here to help.
              Reach out via email or phone — we'll respond fast.
            </p>
          </div>

          {/* Cards */}
          <div className="contact-cards">
            {/* Email Card */}
            <div className="contact-card green">
              <div className="contact-icon-wrap green">✉️</div>
              <div className="contact-card-label green">Email Us</div>
              <div className="contact-card-title">General Inquiries</div>
              <div className="contact-card-value">hello@careerpath.ai</div>
              <div className="contact-card-desc">
                Send us your questions, feedback, or partnership requests. We
                typically reply within 24 hours on business days.
              </div>
              <a
                href="mailto:hello@careerpath.ai"
                className="contact-card-btn green"
              >
                <span>↗</span> Send Email
              </a>
            </div>

            {/* Phone Card */}
            <div className="contact-card purple">
              <div className="contact-icon-wrap purple">📞</div>
              <div className="contact-card-label purple">Call Us</div>
              <div className="contact-card-title">Support Hotline</div>
              <div className="contact-card-value">+1 (800) 555-0192</div>
              <div className="contact-card-desc">
                Prefer to talk? Our support team is available Mon–Fri, 9 AM to 6
                PM IST to walk you through any issue.
              </div>
              <a href="tel:+18005550192" className="contact-card-btn purple">
                <span>↗</span> Call Now
              </a>
            </div>
          </div>

          {/* Status Bar */}
          <div className="contact-info-bar">
            <div className="contact-info-bar-left">
              <div className="contact-status-dot" />
              <div className="contact-info-bar-text">
                <strong>All systems operational</strong> · Average response time
                is under 4 hours
              </div>
            </div>
            <div className="contact-hours-tag">
              ⏰ Mon – Fri · 9 AM – 6 PM IST
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
