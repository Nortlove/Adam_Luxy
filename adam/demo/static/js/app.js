// =============================================================================
// ADAM Demo - Action-Focused Results
// =============================================================================

const API_BASE = '/api';
let currentResult = null;

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    checkPlatformStatus();
    
    document.getElementById('campaign-form').addEventListener('submit', (e) => {
        e.preventDefault();
        analyzeCampaign();
    });
    
    // Brand input → fetch categories with debounce
    let debounceTimer;
    const brandInput = document.getElementById('brand_name');
    brandInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchBrandCategories(brandInput.value.trim());
        }, 500);
    });
});

// =============================================================================
// CATEGORY FACETED SEARCH
// =============================================================================

function normalizeCategoryNames(categories) {
    const seen = new Set();
    const normalized = [];
    
    categories.forEach(cat => {
        let displayName = (cat.display_name || cat.main_category || '')
            .replace(/_/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
        
        // Title case
        displayName = displayName.split(' ').map(word => {
            if (word.length <= 2 && word.toUpperCase() === word) return word;
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        }).join(' ');
        
        // Clean up common names
        displayName = displayName
            .replace('Amazon Fashion', 'Fashion')
            .replace('Clothing Shoes And Jewelry', 'Clothing & Accessories')
            .replace('Sports And Outdoors', 'Sports & Outdoors')
            .replace('Health And Household', 'Health & Household')
            .replace('Beauty And Personal Care', 'Beauty & Personal Care')
            .replace(' > ', ' - ');
        
        const key = displayName.toLowerCase();
        if (!seen.has(key)) {
            seen.add(key);
            normalized.push({ ...cat, display_name: displayName });
        }
    });
    
    return normalized.slice(0, 8);
}

async function fetchBrandCategories(brandName) {
    const categoryList = document.getElementById('product_category');
    const statusEl = document.getElementById('category-status');
    
    if (!brandName || brandName.length < 2) {
        categoryList.innerHTML = '<p class="category-placeholder">Enter brand name to see categories</p>';
        statusEl.textContent = '';
        return;
    }
    
    categoryList.innerHTML = '<p class="category-placeholder">Loading...</p>';
    statusEl.textContent = '';
    
    try {
        const response = await fetch(`${API_BASE}/brands/${encodeURIComponent(brandName)}/categories`);
        const data = await response.json();
        
        if (data.categories && data.categories.length > 0) {
            const normalized = normalizeCategoryNames(data.categories);
            
            let html = '';
            normalized.forEach((cat, idx) => {
                const value = `${cat.main_category}|${cat.subcategory || ''}`;
                html += `
                    <label class="category-checkbox">
                        <input type="checkbox" name="product_category" value="${value}">
                        <span class="category-label">${cat.display_name}</span>
                        <span class="category-count">${cat.product_count}</span>
                    </label>
                `;
            });
            
            categoryList.innerHTML = html;
            statusEl.textContent = `${data.total_products} products found`;
        } else {
            categoryList.innerHTML = '<p class="category-placeholder">No products found</p>';
            statusEl.textContent = 'Will use general models';
        }
    } catch (error) {
        categoryList.innerHTML = '<p class="category-placeholder">Could not load categories</p>';
    }
}

// =============================================================================
// PLATFORM STATUS
// =============================================================================

async function checkPlatformStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const status = await response.json();
        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');
        
        if (status.status === 'operational') {
            dot.className = 'status-dot active';
            text.textContent = 'Ready';
        } else {
            dot.className = 'status-dot';
            text.textContent = 'Connecting';
        }
    } catch (error) {
        document.getElementById('status-dot').className = 'status-dot';
        document.getElementById('status-text').textContent = 'Offline';
    }
}

// =============================================================================
// CAMPAIGN ANALYSIS
// =============================================================================

async function analyzeCampaign() {
    const brand = document.getElementById('brand_name').value.trim();
    const product = document.getElementById('product_name').value.trim();
    const description = document.getElementById('description').value.trim();
    const cta = document.getElementById('call_to_action').value.trim();
    
    if (!brand || !product || !description || !cta) {
        highlightMissingFields();
        return;
    }
    
    const productUrl = document.getElementById('product_url')?.value.trim() || '';
    const targetAudience = document.getElementById('target_audience')?.value.trim() || '';
    
    // Get selected categories (multi-select)
    const checkboxes = document.querySelectorAll('input[name="product_category"]:checked');
    let category = null, subcategory = null;
    if (checkboxes.length > 0) {
        const parts = checkboxes[0].value.split('|');
        category = parts[0] || null;
        subcategory = parts[1] || null;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/analyze-campaign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                brand_name: brand,
                product_name: product,
                description: description,
                call_to_action: cta,
                product_url: productUrl || null,
                target_audience: targetAudience || null,
                category: category,
                subcategory: subcategory
            })
        });
        
        if (!response.ok) throw new Error('Analysis failed');
        
        const result = await response.json();
        currentResult = result;
        
        document.getElementById('processing-time').textContent = `${result.processing_time_ms?.toFixed(0) || 0}ms`;
        renderResults(result);
        
    } catch (error) {
        showError(error.message);
    }
}

function highlightMissingFields() {
    ['brand_name', 'product_name', 'description', 'call_to_action'].forEach(id => {
        const el = document.getElementById(id);
        if (!el.value.trim()) {
            el.style.borderColor = '#ef4444';
            setTimeout(() => el.style.borderColor = '', 2000);
        }
    });
}

// =============================================================================
// UI STATES
// =============================================================================

function showLoading() {
    document.getElementById('results-empty').style.display = 'none';
    document.getElementById('results-content').style.display = 'none';
    document.getElementById('results-loading').style.display = 'flex';
    document.getElementById('analyze-btn').disabled = true;
}

function showError(message) {
    document.getElementById('results-loading').style.display = 'none';
    document.getElementById('results-content').style.display = 'none';
    document.getElementById('results-empty').style.display = 'flex';
    document.getElementById('results-empty').innerHTML = `<p>Error: ${message || 'Please try again.'}</p>`;
    document.getElementById('analyze-btn').disabled = false;
}

// =============================================================================
// RENDER RESULTS - ACTION-FOCUSED
// =============================================================================

function renderResults(result) {
    document.getElementById('results-loading').style.display = 'none';
    document.getElementById('results-empty').style.display = 'none';
    document.getElementById('results-content').style.display = 'block';
    document.getElementById('analyze-btn').disabled = false;
    
    const container = document.getElementById('results-content');
    const segments = result.core_segments || [];
    const stations = result.station_recommendations || [];
    const constructs = result.psychological_constructs || {};
    
    // No segments? Show basic message
    if (segments.length === 0) {
        container.innerHTML = '<p>No targeting recommendations available.</p>';
        return;
    }
    
    // Build tabbed interface for customer types
    let html = '';
    
    // Tab navigation (if multiple segments)
    if (segments.length > 1) {
        html += '<div class="customer-tabs">';
        segments.forEach((seg, i) => {
            html += `<button class="customer-tab ${i === 0 ? 'active' : ''}" onclick="switchTab(${i})">${seg.segment_name}</button>`;
        });
        html += '</div>';
    }
    
    // Tab content for each segment
    segments.forEach((segment, i) => {
        const isActive = i === 0;
        const segmentStations = stations.slice(0, 3); // Top 3 stations
        
        html += `<div class="customer-content ${isActive ? 'active' : ''}" id="tab-${i}">`;
        html += renderActionCard(segment, segmentStations, constructs);
        html += '</div>';
    });
    
    container.innerHTML = html;
}

// =============================================================================
// ACTION CARD - THE MAIN OUTPUT
// =============================================================================

function renderActionCard(segment, stations, constructs) {
    // Primary Action: What station, what words, what timing
    let html = '<div class="recommendation-card">';
    
    // Header: Customer type + confidence
    html += `
        <div class="recommendation-header">
            <span class="recommendation-title">${escapeHtml(segment.segment_name)}</span>
            <span class="recommendation-confidence">${(segment.match_score * 100).toFixed(0)}% match</span>
        </div>
    `;
    
    html += '<div class="recommendation-body">';
    
    // ACTION 1: Script/Hook to use
    html += `
        <div class="action-section">
            <div class="action-label">Use This Hook</div>
            <div class="script-box">${escapeHtml(segment.example_hook || 'No hook available')}</div>
        </div>
    `;
    
    // ACTION 2: Stations to place on
    if (stations.length > 0) {
        html += `
            <div class="action-section">
                <div class="action-label">Place On</div>
        `;
        stations.forEach(station => {
            const name = station.station_name || station.station_format;
            const format = station.station_format;
            html += `
                <div class="station-item">
                    <div>
                        <div class="station-name">${escapeHtml(name)}</div>
                        <div class="station-format">${escapeHtml(format)}</div>
                    </div>
                    <span>${(station.listener_profile_match * 100).toFixed(0)}%</span>
                </div>
            `;
        });
        html += '</div>';
    }
    
    // ACTION 3: Key mechanisms to use
    const mechanisms = [];
    if (segment.primary_mechanism) mechanisms.push(segment.primary_mechanism);
    if (segment.secondary_mechanisms) mechanisms.push(...segment.secondary_mechanisms.slice(0, 2));
    
    if (mechanisms.length > 0) {
        html += `
            <div class="action-section">
                <div class="action-label">Persuasion Approach</div>
                <div class="mechanism-list">
                    ${mechanisms.map(m => `<span class="mechanism-pill">${formatMechanism(m)}</span>`).join('')}
                </div>
            </div>
        `;
    }
    
    // ACTION 4: Frame + Tone (simple one-liner)
    html += `
        <div class="action-section">
            <div class="action-label">Style</div>
            <div class="action-value">${capitalize(segment.recommended_frame || 'balanced')} framing, ${segment.recommended_tone || 'conversational'} tone</div>
        </div>
    `;
    
    // EXPANDABLE: Why this recommendation
    html += `
        <div class="details-section">
            <button class="details-toggle" onclick="toggleDetails(this)">
                <span>Why this recommendation?</span>
                <span>+</span>
            </button>
            <div class="details-content">
                <p style="margin-bottom: 12px;">${escapeHtml(segment.match_explanation || 'Based on psychological profile analysis.')}</p>
    `;
    
    // Show psychological dimensions if available
    if (constructs.regulatory_focus_promotion !== undefined) {
        html += `
            <div class="details-row">
                <span class="details-row-label">Promotion Focus</span>
                <span>${(constructs.regulatory_focus_promotion * 100).toFixed(0)}%</span>
            </div>
            <div class="details-row">
                <span class="details-row-label">Prevention Focus</span>
                <span>${(constructs.regulatory_focus_prevention * 100).toFixed(0)}%</span>
            </div>
        `;
    }
    
    if (constructs.need_for_cognition !== undefined) {
        html += `
            <div class="details-row">
                <span class="details-row-label">Need for Cognition</span>
                <span>${(constructs.need_for_cognition * 100).toFixed(0)}%</span>
            </div>
        `;
    }
    
    html += '</div></div>'; // Close details-content and details-section
    html += '</div>'; // Close recommendation-body
    html += '</div>'; // Close recommendation-card
    
    return html;
}

// =============================================================================
// TAB SWITCHING
// =============================================================================

function switchTab(idx) {
    // Update tab buttons
    document.querySelectorAll('.customer-tab').forEach((tab, i) => {
        tab.classList.toggle('active', i === idx);
    });
    
    // Update tab content
    document.querySelectorAll('.customer-content').forEach((content, i) => {
        content.classList.toggle('active', i === idx);
    });
}

// =============================================================================
// EXPANDABLE DETAILS
// =============================================================================

function toggleDetails(btn) {
    const content = btn.nextElementSibling;
    const isOpen = content.classList.contains('open');
    
    content.classList.toggle('open');
    btn.querySelector('span:last-child').textContent = isOpen ? '+' : '−';
}

// =============================================================================
// UTILITIES
// =============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMechanism(mechanism) {
    if (!mechanism) return '';
    return mechanism.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}
