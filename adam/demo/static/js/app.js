/* =============================================================================
   ADAM Demo Platform - iHeart Showcase
   Psychological Intelligence for Audio Advertising
   ============================================================================= */

const API_BASE = '/api';
let currentResult = null;

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    await checkPlatformStatus();
    setInterval(checkPlatformStatus, 30000);
    
    // Enter key submits form
    document.querySelectorAll('input, textarea').forEach(el => {
        el.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey && el.tagName !== 'TEXTAREA') {
                e.preventDefault();
                analyzeCampaign();
            }
        });
    });
});

// =============================================================================
// PLATFORM STATUS
// =============================================================================

async function checkPlatformStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const status = await response.json();
        updateStatus(status);
    } catch (error) {
        updateStatus({ status: 'error' });
    }
}

function updateStatus(status) {
    const dot = document.querySelector('.status-dot');
    const text = document.querySelector('.status-text');
    
    if (status.status === 'operational') {
        dot.className = 'status-dot active';
        text.textContent = `${status.total_components} components`;
    } else {
        dot.className = 'status-dot';
        text.textContent = 'Connecting...';
    }
}

// =============================================================================
// UI INTERACTIONS
// =============================================================================

function toggleTargeting() {
    const section = document.getElementById('targeting-section');
    const icon = document.getElementById('toggle-icon');
    
    if (section.style.display === 'none') {
        section.style.display = 'block';
        icon.textContent = '−';
    } else {
        section.style.display = 'none';
        icon.textContent = '+';
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
    
    // Validation
    if (!brand || !product || !description || !cta) {
        alert('Please fill in all required fields: Brand, Product, Description, and Call to Action');
        return;
    }
    
    // Get optional fields
    const tagline = document.getElementById('tagline').value.trim();
    const landingUrl = document.getElementById('landing_url').value.trim();
    const productUrl = document.getElementById('product_url').value.trim();
    const targetAudience = document.getElementById('target_audience').value.trim();
    const campaignGoal = document.querySelector('input[name="campaign_goal"]:checked')?.value || 'reach_core';
    
    // Show loading
    showLoading();
    
    try {
        const startTime = performance.now();
        
        // Run campaign analysis with product_url included
        // The server will fetch review intelligence if product_url is provided
        const requestBody = {
            brand_name: brand,
            product_name: product,
            description: description,
            call_to_action: cta,
            tagline: tagline || null,
            landing_url: landingUrl || null,
            target_audience: targetAudience || null,
            campaign_goal: campaignGoal,
        };
        
        // Include product URL for review intelligence
        if (productUrl) {
            requestBody.product_url = productUrl;
            console.log('Including product URL for review intelligence:', productUrl);
        }
        
        const response = await fetch(`${API_BASE}/analyze-campaign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error:', errorText);
            throw new Error('Analysis failed: ' + (response.statusText || 'Unknown error'));
        }
        
        const result = await response.json();
        const clientTime = performance.now() - startTime;
        
        // Log review intelligence status
        if (result.review_intelligence) {
            console.log('Review intelligence received:', result.review_intelligence);
            console.log('Reviews analyzed:', result.review_intelligence.reviews_analyzed);
            console.log('Buyer archetypes:', result.review_intelligence.buyer_archetypes);
            console.log('Language intelligence:', result.review_intelligence.language_intelligence);
        } else {
            console.log('No review intelligence in response');
        }
        
        currentResult = result;
        
        // Update processing time
        document.getElementById('processing-time').textContent = 
            `Analysis: ${result.processing_time_ms.toFixed(0)}ms`;
        
        // Render results
        renderResults(result);
        
    } catch (error) {
        console.error('Analysis error:', error);
        showError(error.message);
    }
}

// =============================================================================
// LOADING & ERROR STATES
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
    document.getElementById('analyze-btn').disabled = false;
    
    document.querySelector('.empty-content h3').textContent = 'Analysis Error';
    document.querySelector('.empty-content p').textContent = message;
}

// =============================================================================
// RENDER RESULTS
// =============================================================================

function renderResults(result) {
    document.getElementById('results-loading').style.display = 'none';
    document.getElementById('results-empty').style.display = 'none';
    document.getElementById('results-content').style.display = 'block';
    document.getElementById('analyze-btn').disabled = false;
    
    const container = document.getElementById('results-content');
    
    // Build HTML
    let html = `
        <!-- Summary Header -->
        <div class="results-header">
            <div class="campaign-echo">
                <span class="campaign-brand">${result.campaign.brand}</span>
                <span class="campaign-product">${result.campaign.product}</span>
            </div>
            <div class="confidence-badge">
                <span class="confidence-value">${(result.overall_confidence * 100).toFixed(0)}%</span>
                <span class="confidence-label">confidence</span>
            </div>
        </div>

        <!-- Core Segments Summary -->
        <div class="section-block">
            <p class="summary-text">${result.core_segment_summary}</p>
        </div>

        <!-- Customer Segments -->
        <div class="section-block">
            <h3 class="section-title">Core Customer Segments</h3>
            <div class="segments-grid">
                ${result.core_segments.map((segment, i) => renderSegmentCard(segment, i === 0)).join('')}
            </div>
        </div>

        <!-- Station Recommendations -->
        <div class="section-block">
            <h3 class="section-title">Recommended Stations</h3>
            <div class="stations-list">
                ${result.station_recommendations.map(station => renderStationCard(station)).join('')}
            </div>
        </div>
    `;
    
    // Custom Audience Analysis (if present)
    if (result.custom_audience) {
        html += renderCustomAudienceSection(result.custom_audience);
    }
    
    // Review Intelligence (if present)
    if (result.review_intelligence && result.review_intelligence.reviews_analyzed > 0) {
        html += renderReviewIntelligenceSection(result.review_intelligence);
    }
    
    // Components footer
    const components = [...result.components_used];
    if (result.review_intelligence) {
        components.push('ReviewIntelligence');
    }
    
    html += `
        <div class="components-footer">
            <span class="components-label">Components used:</span>
            <span class="components-list">${components.join(' · ')}</span>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Animate in
    requestAnimationFrame(() => {
        container.querySelectorAll('.segment-card, .station-card').forEach((el, i) => {
            el.style.animationDelay = `${i * 0.1}s`;
        });
    });
}

// =============================================================================
// SEGMENT CARD
// =============================================================================

function renderSegmentCard(segment, isPrimary) {
    const profile = segment.profile;
    
    return `
        <div class="segment-card ${isPrimary ? 'primary' : ''}">
            <div class="segment-header">
                <span class="segment-icon">${segment.archetype_icon}</span>
                <div class="segment-titles">
                    <h4 class="segment-name">${segment.segment_name}</h4>
                    <span class="segment-archetype">${segment.archetype}</span>
                </div>
                <div class="segment-match">
                    <span class="match-value">${(segment.match_score * 100).toFixed(0)}%</span>
                    <span class="match-label">match</span>
                </div>
            </div>
            
            <p class="segment-explanation">${segment.match_explanation}</p>
            
            <div class="segment-strategy">
                <div class="strategy-header">
                    <span class="strategy-label">Persuasion Strategy</span>
                    <span class="mechanism-badge">${formatMechanism(segment.primary_mechanism)}</span>
                </div>
                <p class="strategy-text">${segment.mechanism_explanation}</p>
            </div>
            
            <div class="segment-messaging">
                <div class="messaging-row">
                    <span class="messaging-label">Tone</span>
                    <span class="messaging-value">${segment.recommended_tone}</span>
                </div>
                <div class="messaging-row">
                    <span class="messaging-label">Frame</span>
                    <span class="messaging-value frame-${segment.recommended_frame}">${segment.recommended_frame === 'gain' ? 'Gain-focused' : segment.recommended_frame === 'loss-avoidance' ? 'Loss-avoidance' : 'Balanced'}</span>
                </div>
            </div>
            
            <div class="segment-example">
                <span class="example-label">Example Hook</span>
                <p class="example-text">"${segment.example_hook}"</p>
            </div>
            
            <div class="segment-research">
                <span class="research-icon">📚</span>
                <span class="research-text">${segment.research_citation}</span>
            </div>
        </div>
    `;
}

// =============================================================================
// STATION CARD
// =============================================================================

function renderStationCard(station) {
    const daypartsHtml = station.best_dayparts.map(dp => {
        const explanation = station.daypart_explanations[dp] || '';
        return `
            <div class="daypart-item">
                <span class="daypart-name">${dp}</span>
                <span class="daypart-reason">${explanation}</span>
            </div>
        `;
    }).join('');
    
    return `
        <div class="station-card">
            <div class="station-header">
                <div class="station-format">
                    <h4 class="format-name">${station.station_format}</h4>
                    <span class="format-desc">${station.station_description}</span>
                </div>
                <div class="station-metrics">
                    <div class="metric">
                        <span class="metric-value">${(station.listener_profile_match * 100).toFixed(0)}%</span>
                        <span class="metric-label">match</span>
                    </div>
                    <div class="metric">
                        <span class="metric-value engagement-${station.expected_engagement.replace(' ', '-')}">${station.expected_engagement}</span>
                        <span class="metric-label">engagement</span>
                    </div>
                </div>
            </div>
            
            <div class="station-reason">
                <p>${station.recommendation_reason}</p>
            </div>
            
            <div class="station-dayparts">
                <span class="dayparts-label">Optimal Dayparts</span>
                <div class="dayparts-list">
                    ${daypartsHtml}
                </div>
            </div>
        </div>
    `;
}

// =============================================================================
// CUSTOM AUDIENCE SECTION
// =============================================================================

function renderCustomAudienceSection(custom) {
    const stationsHtml = custom.station_recommendations.map(s => `
        <div class="mini-station">
            <span class="mini-station-format">${s.station_format}</span>
            <span class="mini-station-reason">${s.recommendation_reason.substring(0, 100)}...</span>
        </div>
    `).join('');
    
    return `
        <div class="section-block custom-audience">
            <h3 class="section-title">Your Specified Audience</h3>
            
            <div class="custom-header">
                <div class="custom-audience-desc">"${custom.audience_description}"</div>
                <div class="custom-archetype">
                    <span class="archetype-inferred">Inferred as</span>
                    <span class="archetype-name">${custom.inferred_archetype}</span>
                </div>
            </div>
            
            <div class="custom-contrast">
                <span class="contrast-icon">⚡</span>
                <p>${custom.contrast_with_core}</p>
            </div>
            
            <div class="custom-strategy">
                <h4>How to Persuade This Audience</h4>
                <p class="strategy-text">${custom.persuasion_strategy}</p>
                
                <div class="custom-mechanisms">
                    ${custom.recommended_mechanisms.map(m => `<span class="mechanism-tag">${formatMechanism(m)}</span>`).join('')}
                </div>
                
                <div class="custom-messaging">
                    <span class="messaging-label">Suggested Messaging</span>
                    <p class="messaging-example">"${custom.messaging_approach}"</p>
                </div>
            </div>
            
            <div class="custom-stations">
                <h4>Stations for This Audience</h4>
                ${stationsHtml}
            </div>
        </div>
    `;
}

// =============================================================================
// REVIEW INTELLIGENCE SECTION
// =============================================================================

function renderReviewIntelligenceSection(intel) {
    const archetypeBars = Object.entries(intel.buyer_archetypes || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([archetype, score]) => `
            <div class="archetype-bar-row">
                <span class="archetype-bar-label">${archetype}</span>
                <div class="archetype-bar-container">
                    <div class="archetype-bar-fill" style="width: ${score * 100}%"></div>
                </div>
                <span class="archetype-bar-value">${(score * 100).toFixed(0)}%</span>
            </div>
        `).join('');
    
    const mechanismBars = Object.entries(intel.mechanism_predictions || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([mech, score]) => `
            <div class="mechanism-bar-row">
                <span class="mechanism-bar-label">${formatMechanism(mech)}</span>
                <div class="mechanism-bar-container">
                    <div class="mechanism-bar-fill" style="width: ${score * 100}%"></div>
                </div>
                <span class="mechanism-bar-value">${(score * 100).toFixed(0)}%</span>
            </div>
        `).join('');
    
    const phrases = (intel.language_intelligence?.phrases || []).slice(0, 5);
    const powerWords = (intel.language_intelligence?.power_words || []).slice(0, 8);
    
    return `
        <div class="section-block review-intelligence">
            <h3 class="section-title">
                <span class="ri-icon">📊</span>
                Customer Intelligence from Reviews
            </h3>
            
            <div class="ri-header">
                <div class="ri-stat">
                    <span class="ri-stat-value">${intel.reviews_analyzed}</span>
                    <span class="ri-stat-label">Reviews Analyzed</span>
                </div>
                <div class="ri-stat">
                    <span class="ri-stat-value">${intel.sources_used?.length || 0}</span>
                    <span class="ri-stat-label">Sources</span>
                </div>
                <div class="ri-stat">
                    <span class="ri-stat-value">${intel.avg_rating?.toFixed(1) || 'N/A'}</span>
                    <span class="ri-stat-label">Avg Rating</span>
                </div>
                <div class="ri-stat">
                    <span class="ri-stat-value">${(intel.overall_confidence * 100).toFixed(0)}%</span>
                    <span class="ri-stat-label">Confidence</span>
                </div>
            </div>
            
            <div class="ri-grid">
                <div class="ri-card">
                    <h4>Real Buyer Archetypes</h4>
                    <p class="ri-note">Who actually buys this product:</p>
                    <div class="archetype-bars">
                        ${archetypeBars}
                    </div>
                    <div class="ri-dominant">
                        Dominant: <strong>${intel.dominant_archetype}</strong> (${(intel.archetype_confidence * 100).toFixed(0)}% confidence)
                    </div>
                </div>
                
                <div class="ri-card">
                    <h4>Predicted Mechanism Effectiveness</h4>
                    <p class="ri-note">Based on customer psychology:</p>
                    <div class="mechanism-bars">
                        ${mechanismBars}
                    </div>
                </div>
            </div>
            
            <div class="ri-grid">
                <div class="ri-card">
                    <h4>Customer Language</h4>
                    <p class="ri-note">Use these phrases in your ad copy:</p>
                    <div class="ri-phrases">
                        ${phrases.map(p => `<span class="ri-phrase">"${p}"</span>`).join('')}
                    </div>
                    <div class="ri-power-words">
                        <span class="ri-pw-label">Power words:</span>
                        ${powerWords.map(w => `<span class="ri-power-word">${w}</span>`).join('')}
                    </div>
                </div>
                
                <div class="ri-card">
                    <h4>Purchase Motivations</h4>
                    <p class="ri-note">Why customers buy:</p>
                    <div class="ri-motivations">
                        ${(intel.purchase_motivations || []).slice(0, 5).map(m => `
                            <span class="ri-motivation ${m === intel.primary_motivation ? 'primary' : ''}">${formatMechanism(m)}</span>
                        `).join('')}
                    </div>
                    ${intel.primary_motivation ? `
                        <div class="ri-primary-motivation">
                            Primary driver: <strong>${formatMechanism(intel.primary_motivation)}</strong>
                        </div>
                    ` : ''}
                </div>
            </div>
            
            ${intel.ideal_customer ? `
                <div class="ri-ideal">
                    <h4>Ideal Customer Profile</h4>
                    <p class="ri-note">From 5-star reviewers - your best targets:</p>
                    <div class="ri-ideal-content">
                        <span class="ri-ideal-archetype">${intel.ideal_customer.archetype}</span>
                        <span class="ri-ideal-conf">${(intel.ideal_customer.archetype_confidence * 100).toFixed(0)}% match</span>
                    </div>
                    ${intel.ideal_customer.characteristic_phrases?.length ? `
                        <div class="ri-ideal-phrases">
                            ${intel.ideal_customer.characteristic_phrases.slice(0, 3).map(p => `<span class="ri-phrase">"${p}"</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            ` : ''}
        </div>
    `;
}

// =============================================================================
// UTILITIES
// =============================================================================

function formatMechanism(mechanism) {
    if (!mechanism) return '';
    return mechanism
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}
