"""Custom CSS for the insurance demo dashboard."""

DASHBOARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {
    --redis-red: #DC382D;
    --openshift-blue: #0066CC;
    --success-green: #3D9970;
    --warning-orange: #FF851B;
    --inactive-gray: #6c757d;
    --card-bg: #1a1d24;
    --card-border: #2d3340;
    --text-primary: #f0f2f5;
    --text-muted: #9aa3b2;
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

.stApp {
    background: linear-gradient(160deg, #0d1117 0%, #161b22 45%, #1a2332 100%);
    color: var(--text-primary);
}

.block-container {
    padding-top: 1.5rem;
    max-width: 1400px;
}

h1, h2, h3 {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

.dashboard-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, var(--redis-red), #ff6b5b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
}

.dashboard-subtitle {
    color: var(--text-muted);
    font-size: 1.05rem;
    margin-bottom: 1.5rem;
}

.journey-pipeline {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0;
    padding: 1rem 0;
}

.journey-arrow {
    color: var(--inactive-gray);
    font-size: 1.25rem;
    line-height: 1;
    margin: 0.15rem 0;
}

.journey-step {
    width: 100%;
    max-width: 520px;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    border: 1px solid var(--card-border);
    background: var(--card-bg);
    transition: box-shadow 0.3s, border-color 0.3s;
}

.journey-step.pending { opacity: 0.35; }
.journey-step.active {
    border-color: var(--openshift-blue);
    box-shadow: 0 0 20px rgba(0, 102, 204, 0.35);
}
.journey-step.complete {
    border-color: var(--success-green);
    box-shadow: 0 0 12px rgba(61, 153, 112, 0.2);
}

.step-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-weight: 600;
    font-size: 1rem;
    margin-bottom: 0.5rem;
}

.step-icon { font-size: 1.2rem; }

.step-explanation {
    color: var(--text-muted);
    font-size: 0.85rem;
}

.component-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.5rem;
}

.component-card h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
    color: var(--redis-red);
}

.component-stat {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    padding: 0.15rem 0;
}
</style>
"""
