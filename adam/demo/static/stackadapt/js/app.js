/* ========================================================================
   INFORMATIV AI × StackAdapt Demo — Frontend Logic
   ======================================================================== */

const API_BASE = '';
let scenarios = [];
let currentResult = null;
let ndfRadarChart = null;
let mechBarChart = null;
let learningChart = null;

// ---- Utility ----
function formatNumber(n) {
    if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return n.toLocaleString();
}

function pct(v) {
    return Math.round(v * 100) + '%';
}

// ---- Chart.js Global Config ----
Chart.defaults.color = '#8b99b0';
Chart.defaults.borderColor = 'rgba(45, 58, 80, 0.5)';
Chart.defaults.font.family = "'Inter', sans-serif";

// ---- Init ----
document.addEventListener('DOMContentLoaded', async () => {
    await loadPopulationStats();
    await loadScenarios();
    await loadCategories();
});

async function loadPopulationStats() {
    try {
        const resp = await fetch(API_BASE + '/api/population');
        const data = await resp.json();
        document.getElementById('statReviews').textContent = '1B+';
    } catch (e) {
        console.error('Failed to load population stats:', e);
    }
}

async function loadScenarios() {
    try {
        const resp = await fetch(API_BASE + '/api/scenarios');
        const data = await resp.json();
        scenarios = data.scenarios || [];
        renderScenarios();
    } catch (e) {
        console.error('Failed to load scenarios:', e);
    }
}

async function loadCategories() {
    try {
        const resp = await fetch(API_BASE + '/api/categories');
        const data = await resp.json();
        const sel = document.getElementById('category');
        sel.innerHTML = '<option value="">Select category...</option>';
        (data.categories || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c.replace(/_/g, ' ');
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load categories:', e);
    }
}

// ---- Scenario Icons ----
const SCENARIO_ICONS = {
    running: '🏃', headphones: '🎧', heart: '💚', tool: '🔧', sparkle: '✨',
};
const SCENARIO_COLORS = ['#4f8ff7', '#06d6a0', '#8b5cf6', '#f59e0b', '#ec4899'];

function renderScenarios() {
    const grid = document.getElementById('scenariosGrid');
    grid.innerHTML = '';
    scenarios.forEach((sc, i) => {
        const btn = document.createElement('button');
        btn.className = 'scenario-btn';
        btn.dataset.id = sc.id;
        btn.innerHTML = `
            <div class="scenario-icon" style="background:${SCENARIO_COLORS[i % 5]}20;color:${SCENARIO_COLORS[i % 5]}">
                ${SCENARIO_ICONS[sc.icon] || '📦'}
            </div>
            <div class="scenario-info">
                <div class="name">${sc.name}</div>
                <div class="subtitle">${sc.subtitle}</div>
            </div>
        `;
        btn.onclick = () => selectScenario(sc, btn);
        grid.appendChild(btn);
    });
}

function selectScenario(sc, btn) {
    document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('segmentName').value = sc.segment_name;
    document.getElementById('productName').value = sc.product_name;
    document.getElementById('adCopy').value = sc.ad_copy;
    document.getElementById('sampleReview').value = sc.sample_review;
    const sel = document.getElementById('category');
    for (let opt of sel.options) {
        if (opt.value === sc.category) { sel.value = sc.category; break; }
    }
    // Don't auto-run — let the user click "Run" manually
}

// ---- Main Analysis ----
async function runAnalysis() {
    const btn = document.getElementById('analyzeBtn');
    btn.classList.add('loading');
    btn.textContent = 'Analyzing…';

    document.getElementById('resultsPlaceholder').style.display = 'none';
    document.getElementById('resultsPanel').classList.add('visible');

    const fill = document.getElementById('processingFill');
    fill.style.width = '0%';
    setTimeout(() => fill.style.width = '60%', 50);

    try {
        const payload = {
            segment_name: document.getElementById('segmentName').value,
            category: document.getElementById('category').value,
            product_name: document.getElementById('productName').value,
            ad_copy: document.getElementById('adCopy').value,
            sample_review: document.getElementById('sampleReview').value,
        };

        const resp = await fetch(API_BASE + '/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        currentResult = await resp.json();
        fill.style.width = '100%';
        renderResults(currentResult);
    } catch (e) {
        console.error('Analysis failed:', e);
        fill.style.width = '0%';
    }

    btn.classList.remove('loading');
    btn.textContent = 'Run INFORMATIV AI Analysis';
}

// ---- Render All Results ----
function renderResults(data) {
    renderStackAdaptReturn(data);
    renderSummary(data);
    renderNdfRadar(data);
    renderMechBar(data);
    renderMechList(data);
    renderCopyOptimization(data);
    renderNdfDetail(data);
    renderLearningChart(data);
    renderArchetypeBars(data);

    document.getElementById('returnCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============================================================
// RETURNED TO STACKADAPT SYSTEM — The headline section
// ============================================================
function renderStackAdaptReturn(data) {
    const lift = data.expected_lift;
    const payload = data.stackadapt_return_payload;
    const seg = data.segment;
    const primary = data.mechanism_ranking[0];

    // Lift stats
    const liftContainer = document.getElementById('liftStats');
    liftContainer.innerHTML = `
        <div class="lift-row">
            <div class="lift-card lift-ctr">
                <div class="lift-label">Expected Click-Through Lift</div>
                <div class="lift-value">+${lift.ctr_lift_low}% – ${lift.ctr_lift_high}%</div>
                <div class="lift-confidence">${lift.confidence_level} confidence</div>
            </div>
            <div class="lift-card lift-purchase">
                <div class="lift-label">Expected Purchase Lift</div>
                <div class="lift-value">+${lift.purchase_lift_low}% – ${lift.purchase_lift_high}%</div>
                <div class="lift-confidence">${lift.confidence_level} confidence</div>
            </div>
            <div class="lift-card lift-method">
                <div class="lift-label">Methodology</div>
                <div class="lift-method-text">${lift.methodology}</div>
                <div class="lift-confidence">${lift.improvement_room}% optimization headroom</div>
            </div>
        </div>
    `;

    // Return payload summary
    const ds = data.decision_style || {};
    const secondary = data.mechanism_ranking[1];
    const payloadGrid = document.getElementById('returnPayloadGrid');
    payloadGrid.innerHTML = `
        <div class="return-item">
            <div class="return-key">Granular Customer Type</div>
            <div class="return-val return-type-label">${seg.granular_type_label}</div>
            <div class="return-note">Resolved from ${formatNumber(data.meta.granular_types_resolved)} possible types</div>
        </div>
        <div class="return-item">
            <div class="return-key">Decision Style (ELM)</div>
            <div class="return-val" style="color:var(--accent-amber)">${ds.label || 'Mixed'}</div>
            <div class="return-note">${ds.academic_basis || ''}</div>
        </div>
        <div class="return-item">
            <div class="return-key">Primary Mechanism</div>
            <div class="return-val" style="color:var(--accent-cyan)">${primary.label} (${pct(primary.combined_score)})</div>
            <div class="return-note">${primary.elm_route_label || ''}</div>
        </div>
        <div class="return-item">
            <div class="return-key">Secondary Mechanism</div>
            <div class="return-val">${secondary.label} (${pct(secondary.combined_score)})</div>
            <div class="return-note">${secondary.elm_route_label || ''}</div>
        </div>
        <div class="return-item">
            <div class="return-key">Creative Frame</div>
            <div class="return-val">${payload.creative_parameters.frame} / ${payload.creative_parameters.energy_level} / ${payload.creative_parameters.voice_style}</div>
        </div>
        <div class="return-item">
            <div class="return-key">Suggested CTA</div>
            <div class="return-val" style="color:var(--accent-green)">${payload.creative_parameters.suggested_cta}</div>
        </div>
        <div class="return-item">
            <div class="return-key">Processing Time</div>
            <div class="return-val">${data.meta.processing_time_ms}ms</div>
        </div>
    `;

    // JSON preview
    const jsonEl = document.getElementById('jsonPreview');
    jsonEl.textContent = JSON.stringify(payload, null, 2);
}

// ---- Summary Stats ----
function renderSummary(data) {
    const seg = data.segment;
    const meta = data.meta;
    document.getElementById('procTime').textContent = `${meta.processing_time_ms}ms`;
    document.getElementById('summaryTitle').textContent = seg.name + ' — Intelligence Detail';

    const container = document.getElementById('segmentSummary');
    const alignment = data.alignment;
    const primary = data.mechanism_ranking[0];

    container.innerHTML = `
        <div class="summary-stat">
            <div class="value value-cyan">${seg.detected_archetype.charAt(0).toUpperCase() + seg.detected_archetype.slice(1)}</div>
            <div class="label">Base Archetype</div>
        </div>
        <div class="summary-stat">
            <div class="value value-purple">${seg.archetype_population_share}%</div>
            <div class="label">Population Share</div>
        </div>
        <div class="summary-stat">
            <div class="value value-green">${primary.label}</div>
            <div class="label">Top Mechanism</div>
        </div>
        <div class="summary-stat">
            <div class="value value-amber">${pct(primary.combined_score)}</div>
            <div class="label">Combined Score</div>
        </div>
        <div class="summary-stat">
            <div class="value value-blue">${pct(alignment.overall_alignment)}</div>
            <div class="label">Current Alignment</div>
        </div>
    `;
}

// ---- NDF Radar Chart ----
function renderNdfRadar(data) {
    const ndf = data.ndf_profile;
    const dims = Object.keys(ndf.segment_ndf);
    const labels = dims.map(d => ndf.dim_labels[d] || d);
    const segValues = dims.map(d => ndf.segment_ndf[d]);
    const popValues = dims.map(d => (ndf.population_ndf[d] || 0));
    const archValues = dims.map(d => (ndf.archetype_ndf[d] || 0));

    if (ndfRadarChart) ndfRadarChart.destroy();
    const ctx = document.getElementById('ndfRadar').getContext('2d');
    ndfRadarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'This Segment', data: segValues,
                    borderColor: 'rgba(79,143,247,0.9)', backgroundColor: 'rgba(79,143,247,0.15)',
                    borderWidth: 2.5, pointRadius: 4, pointBackgroundColor: '#4f8ff7',
                },
                {
                    label: 'Population', data: popValues,
                    borderColor: 'rgba(139,92,246,0.6)', backgroundColor: 'rgba(139,92,246,0.05)',
                    borderWidth: 1.5, borderDash: [4,4], pointRadius: 3, pointBackgroundColor: '#8b5cf6',
                },
                {
                    label: 'Archetype Avg', data: archValues,
                    borderColor: 'rgba(6,214,160,0.6)', backgroundColor: 'rgba(6,214,160,0.05)',
                    borderWidth: 1.5, borderDash: [2,2], pointRadius: 3, pointBackgroundColor: '#06d6a0',
                },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { r: {
                beginAtZero: true, max: 1,
                ticks: { display: false, stepSize: 0.2 },
                grid: { color: 'rgba(45,58,80,0.4)' },
                angleLines: { color: 'rgba(45,58,80,0.3)' },
                pointLabels: { font: { size: 10, weight: '600' }, color: '#8b99b0' },
            }},
        },
    });
}

// ---- Mechanism Bar Chart ----
function renderMechBar(data) {
    const ranking = data.mechanism_ranking;
    const labels = ranking.map(m => m.label);
    const ndfScores = ranking.map(m => m.ndf_susceptibility);
    const effScores = ranking.map(m => m.population_effectiveness);

    if (mechBarChart) mechBarChart.destroy();
    const ctx = document.getElementById('mechBar').getContext('2d');
    mechBarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { label: 'NDF Susceptibility', data: ndfScores, backgroundColor: 'rgba(79,143,247,0.7)', borderRadius: 4, barPercentage: 0.7 },
                { label: 'Population Effectiveness', data: effScores, backgroundColor: 'rgba(6,214,160,0.6)', borderRadius: 4, barPercentage: 0.7 },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
            plugins: { legend: { position: 'top', labels: { boxWidth: 12, padding: 12, font: { size: 10 } } } },
            scales: {
                x: { beginAtZero: true, max: 1, grid: { color: 'rgba(45,58,80,0.3)' } },
                y: { grid: { display: false }, ticks: { font: { size: 11, weight: '600' } } },
            },
        },
    });
}

// ---- Mechanism Ranking List ----
function renderMechList(data) {
    const container = document.getElementById('mechList');
    container.innerHTML = '';

    // Decision Style header
    const ds = data.decision_style;
    if (ds) {
        const dsHeader = document.createElement('div');
        dsHeader.className = 'decision-style-header';
        dsHeader.innerHTML = `
            <div class="ds-badge ${ds.style.replace('_', '-')}">${ds.label}</div>
        `;
        container.appendChild(dsHeader);
    }

    data.mechanism_ranking.forEach((m, i) => {
        const rankClass = i < 3 ? `rank-${i + 1}` : '';
        const routeClass = m.elm_route === 'central' ? 'route-central' : 'route-peripheral';
        const routeLabel = m.elm_route === 'central' ? 'Central' : 'Peripheral';
        const item = document.createElement('div');
        item.className = 'mechanism-item';
        item.innerHTML = `
            <div class="mechanism-rank ${rankClass}">${i + 1}</div>
            <div class="mechanism-info">
                <div class="mechanism-name">${m.label} <span class="elm-route-tag ${routeClass}">${routeLabel}</span></div>
                <div class="mechanism-desc">${m.description}</div>
            </div>
            <div class="mechanism-scores">
                <div class="mechanism-score"><div class="val value-blue">${pct(m.ndf_susceptibility)}</div><div class="lbl">NDF</div></div>
                <div class="mechanism-score"><div class="val value-cyan">${pct(m.population_effectiveness)}</div><div class="lbl">Pop. Eff.</div></div>
                <div class="mechanism-score"><div class="val value-amber">${pct(m.combined_score)}</div><div class="lbl">Combined</div></div>
            </div>
        `;
        container.appendChild(item);
    });
}

// ---- Copy Optimization ----
function renderCopyOptimization(data) {
    const co = data.copy_optimization;
    const al = data.alignment;

    const meter = document.getElementById('alignmentMeter');
    const alPct = Math.round(al.overall_alignment * 100);
    const alClass = alPct > 85 ? 'alignment-high' : alPct > 70 ? 'alignment-mid' : 'alignment-low';
    meter.innerHTML = `
        <div class="alignment-circle ${alClass}">${alPct}%</div>
        <div class="alignment-info">
            <div class="verdict">${al.verdict}</div>
            <div class="detail">Current ad copy alignment with target segment psychology</div>
        </div>
    `;

    const container = document.getElementById('copyComparison');
    container.innerHTML = `
        <div class="copy-panel original">
            <div class="panel-label">Current Ad Copy (StackAdapt Input)</div>
            <div class="copy-text">${co.original_copy}</div>
        </div>
        <div class="copy-panel optimized">
            <div class="panel-label">INFORMATIV AI Optimization Recommendations</div>
            <div class="optimization-notes">
                ${co.optimization_notes.map(n => `<div class="opt-note">${n}</div>`).join('')}
            </div>
            <div style="margin-top:16px;padding:12px;background:rgba(6,214,160,0.08);border-radius:8px;border:1px solid rgba(6,214,160,0.2)">
                <div style="font-size:11px;font-weight:700;color:var(--accent-cyan);margin-bottom:6px">SUGGESTED CTA</div>
                <div style="font-size:14px;font-weight:700">${co.suggested_cta}</div>
            </div>
        </div>
    `;
}

// ---- NDF Dimension Detail ----
function renderNdfDetail(data) {
    const ndf = data.ndf_profile;
    const dims = Object.keys(ndf.segment_ndf);
    const container = document.getElementById('ndfDetailGrid');
    container.innerHTML = '';

    dims.forEach(dim => {
        const val = ndf.segment_ndf[dim];
        const label = ndf.dim_labels[dim] || dim;
        const desc = ndf.dim_descriptions[dim] || '';
        const barWidth = Math.max(Math.abs(val) * 100, 5);

        const card = document.createElement('div');
        card.className = 'ndf-dim-card';
        card.innerHTML = `
            <div class="ndf-dim-header">
                <div class="ndf-dim-name">${label}</div>
                <div class="ndf-dim-value">${val >= 0 ? '+' : ''}${val.toFixed(3)}</div>
            </div>
            <div class="ndf-dim-bar"><div class="fill" style="width:${barWidth}%"></div></div>
            <div class="ndf-dim-desc">${desc}</div>
        `;
        container.appendChild(card);
    });
}

// ---- Learning Trajectory Chart ----
function renderLearningChart(data) {
    const trajectory = data.learning_trajectory;
    if (!trajectory || !trajectory.length) return;

    if (learningChart) learningChart.destroy();
    const ctx = document.getElementById('learningChart').getContext('2d');
    learningChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trajectory.map(t => t.iteration),
            datasets: [
                {
                    label: 'Cumulative Success Rate', data: trajectory.map(t => t.cumulative_success_rate),
                    borderColor: '#4f8ff7', backgroundColor: 'rgba(79,143,247,0.1)', fill: true, tension: 0.4, pointRadius: 3, pointBackgroundColor: '#4f8ff7',
                },
                {
                    label: 'Primary Mechanism Allocation', data: trajectory.map(t => t.primary_allocation),
                    borderColor: '#06d6a0', backgroundColor: 'rgba(6,214,160,0.1)', fill: true, tension: 0.4, pointRadius: 3, pointBackgroundColor: '#06d6a0',
                },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'top', labels: { boxWidth: 12, padding: 16, font: { size: 11 } } } },
            scales: {
                x: { title: { display: true, text: 'Iteration', font: { size: 11 } }, grid: { color: 'rgba(45,58,80,0.3)' } },
                y: { beginAtZero: true, max: 1, title: { display: true, text: 'Score', font: { size: 11 } }, grid: { color: 'rgba(45,58,80,0.3)' } },
            },
        },
    });
}

// ---- Archetype Distribution Bars ----
function renderArchetypeBars(data) {
    const dist = data.archetype_distribution || {};
    const global = dist.global || {};
    const container = document.getElementById('archetypeBars');

    if (!container) return;
    container.innerHTML = '';

    const entries = Object.entries(global).sort((a, b) => b[1] - a[1]).slice(0, 8);
    if (entries.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px">No archetype data available</div>';
        return;
    }

    const maxVal = entries[0][1];

    entries.forEach(([name, pctVal], i) => {
        const width = Math.max((pctVal / maxVal) * 100, 3);
        const row = document.createElement('div');
        row.className = 'arch-bar-row';
        row.innerHTML = `
            <div class="arch-bar-label">${name.charAt(0).toUpperCase() + name.slice(1)}</div>
            <div class="arch-bar-track">
                <div class="arch-bar-fill bar-color-${i}" style="width:${width}%">${pctVal.toFixed(1)}%</div>
            </div>
            <div class="arch-bar-value">${pctVal.toFixed(1)}%</div>
        `;
        container.appendChild(row);
    });

    const countEl = document.getElementById('archReviewCount');
    if (countEl && data.meta) countEl.textContent = formatNumber(data.meta.reviews_analyzed);
}
