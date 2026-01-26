/**
 * ADAM Desktop Behavioral Analytics SDK
 * 
 * Browser-based JavaScript SDK for collecting implicit behavioral signals
 * from desktop interactions.
 * 
 * Signals collected:
 * - Cursor trajectories between decision points
 * - Cursor movements and hover patterns
 * - Keystroke dynamics (anonymized)
 * - Scroll behavior
 * 
 * Usage:
 *   const adam = new ADAMDesktopSDK({
 *     apiEndpoint: 'https://api.adam.example.com',
 *     sessionId: 'optional-session-id',
 *     userId: 'optional-user-id',
 *   });
 *   adam.start();
 *   // ... user interacts with page ...
 *   adam.end({ outcomeType: 'conversion', outcomeValue: 1.0 });
 */

class ADAMDesktopSDK {
  constructor(options = {}) {
    this.apiEndpoint = options.apiEndpoint || '/api/behavioral/desktop';
    this.sessionId = options.sessionId || null;
    this.userId = options.userId || null;
    this.batchSize = options.batchSize || 50;
    this.batchIntervalMs = options.batchIntervalMs || 2000;
    this.debug = options.debug || false;
    
    // State
    this.isActive = false;
    this.cursorMoves = [];
    this.trajectoryStart = null;
    this.trajectoryPoints = [];
    this.lastMoveTime = 0;
    this.lastX = 0;
    this.lastY = 0;
    this.lastVelocity = 0;
    
    // Keystroke state
    this.keystrokeBuffer = [];
    this.lastKeyUp = 0;
    
    // Scroll state
    this.lastScrollY = 0;
    this.lastScrollTime = 0;
    
    // Hover state
    this.hoverElement = null;
    this.hoverStartTime = 0;
    this.hoverMicroMovements = 0;
    
    // Batch send interval
    this.batchInterval = null;
    
    // Bind methods
    this._onMouseMove = this._onMouseMove.bind(this);
    this._onMouseDown = this._onMouseDown.bind(this);
    this._onMouseUp = this._onMouseUp.bind(this);
    this._onClick = this._onClick.bind(this);
    this._onScroll = this._onScroll.bind(this);
    this._onKeyDown = this._onKeyDown.bind(this);
    this._onKeyUp = this._onKeyUp.bind(this);
  }
  
  /**
   * Start collecting behavioral signals.
   */
  async start() {
    if (this.isActive) {
      this._log('Already active');
      return;
    }
    
    // Start session on server
    const response = await this._fetch('/session/start', {
      session_id: this.sessionId,
      user_id: this.userId,
      page_url: window.location.href,
      viewport_width: window.innerWidth,
      viewport_height: window.innerHeight,
      device_info: this._getDeviceInfo(),
    });
    
    this.sessionId = response.session_id;
    this.isActive = true;
    
    // Attach event listeners
    document.addEventListener('mousemove', this._onMouseMove, { passive: true });
    document.addEventListener('mousedown', this._onMouseDown, { passive: true });
    document.addEventListener('mouseup', this._onMouseUp, { passive: true });
    document.addEventListener('click', this._onClick, { passive: true });
    document.addEventListener('scroll', this._onScroll, { passive: true });
    document.addEventListener('keydown', this._onKeyDown, { passive: true });
    document.addEventListener('keyup', this._onKeyUp, { passive: true });
    
    // Start batch send interval
    this.batchInterval = setInterval(() => this._sendBatch(), this.batchIntervalMs);
    
    this._log('Started session:', this.sessionId);
  }
  
  /**
   * Stop collecting and end session.
   */
  async end(options = {}) {
    if (!this.isActive) {
      this._log('Not active');
      return;
    }
    
    // Remove event listeners
    document.removeEventListener('mousemove', this._onMouseMove);
    document.removeEventListener('mousedown', this._onMouseDown);
    document.removeEventListener('mouseup', this._onMouseUp);
    document.removeEventListener('click', this._onClick);
    document.removeEventListener('scroll', this._onScroll);
    document.removeEventListener('keydown', this._onKeyDown);
    document.removeEventListener('keyup', this._onKeyUp);
    
    // Clear interval
    if (this.batchInterval) {
      clearInterval(this.batchInterval);
      this.batchInterval = null;
    }
    
    // Send remaining batch
    await this._sendBatch();
    
    // End keystroke sequence if any
    await this._sendKeystrokeSequence();
    
    // End session on server
    const response = await this._fetch('/session/end', {
      session_id: this.sessionId,
      outcome_type: options.outcomeType || null,
      outcome_value: options.outcomeValue || null,
    });
    
    this.isActive = false;
    this._log('Ended session:', response);
    
    return response;
  }
  
  /**
   * Mark a trajectory start point (e.g., when options appear).
   */
  startTrajectory(options = {}) {
    this.trajectoryStart = {
      x: this.lastX,
      y: this.lastY,
      time: performance.now(),
      element: options.startElement || null,
      targetOptions: options.targetOptions || [],
    };
    this.trajectoryPoints = [[this.lastX, this.lastY, 0]];
    this._log('Trajectory started at:', this.lastX, this.lastY);
  }
  
  /**
   * Mark trajectory end and send to server.
   */
  async endTrajectory(options = {}) {
    if (!this.trajectoryStart) {
      this._log('No trajectory started');
      return null;
    }
    
    const now = performance.now();
    const duration = now - this.trajectoryStart.time;
    
    // Calculate trajectory metrics
    const metrics = this._calculateTrajectoryMetrics(
      this.trajectoryStart.x,
      this.trajectoryStart.y,
      this.lastX,
      this.lastY,
      this.trajectoryPoints
    );
    
    // Send trajectory
    const response = await this._fetch('/cursor/trajectory', {
      session_id: this.sessionId,
      start_x: this.trajectoryStart.x,
      start_y: this.trajectoryStart.y,
      end_x: this.lastX,
      end_y: this.lastY,
      area_under_curve: metrics.auc,
      maximum_absolute_deviation: metrics.mad,
      x_flips: metrics.xFlips,
      y_flips: metrics.yFlips,
      initiation_time_ms: Math.round(metrics.initiationTime),
      movement_time_ms: Math.round(duration - metrics.initiationTime),
      start_element: this.trajectoryStart.element,
      end_element: options.endElement || null,
      target_options: this.trajectoryStart.targetOptions,
      chosen_option: options.chosenOption || null,
      trajectory_points: this._samplePoints(this.trajectoryPoints, 20),
    });
    
    this.trajectoryStart = null;
    this.trajectoryPoints = [];
    
    this._log('Trajectory sent:', response);
    return response;
  }
  
  // =========================================================================
  // PRIVATE METHODS
  // =========================================================================
  
  _onMouseMove(event) {
    const now = performance.now();
    const x = event.clientX;
    const y = event.clientY;
    
    // Calculate velocity
    const dt = now - this.lastMoveTime;
    const dx = x - this.lastX;
    const dy = y - this.lastY;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const velocity = dt > 0 ? (distance / dt) * 1000 : 0; // px/sec
    
    // Calculate acceleration
    const acceleration = dt > 0 ? (velocity - this.lastVelocity) / dt * 1000 : 0;
    
    // Add to buffer
    this.cursorMoves.push({
      x,
      y,
      velocity,
      velocity_x: dt > 0 ? (dx / dt) * 1000 : 0,
      velocity_y: dt > 0 ? (dy / dt) * 1000 : 0,
      acceleration,
      element: this._getElementUnderCursor(event),
      timestamp: now,
    });
    
    // Update trajectory points if tracking
    if (this.trajectoryStart) {
      this.trajectoryPoints.push([x, y, Math.round(now - this.trajectoryStart.time)]);
    }
    
    // Check for hover
    this._checkHover(event);
    
    // Update state
    this.lastMoveTime = now;
    this.lastX = x;
    this.lastY = y;
    this.lastVelocity = velocity;
  }
  
  _onMouseDown(event) {
    // Could start trajectory on mousedown for certain elements
  }
  
  _onMouseUp(event) {
    // Could end trajectory on mouseup
  }
  
  _onClick(event) {
    // Check if we should end a trajectory
    if (this.trajectoryStart) {
      const element = event.target;
      const option = element.getAttribute('data-adam-option') ||
                     element.getAttribute('data-option') ||
                     element.textContent?.substring(0, 50);
      
      this.endTrajectory({
        endElement: this._getElementId(element),
        chosenOption: option,
      });
    }
    
    // End any active hover
    this._endHover();
  }
  
  _onScroll(event) {
    const now = performance.now();
    const scrollY = window.scrollY;
    const scrollX = window.scrollX;
    const dt = now - this.lastScrollTime;
    
    // Calculate velocity and check for reversal
    const velocity = dt > 0 ? Math.abs(scrollY - this.lastScrollY) / dt * 1000 : 0;
    const isReversal = (scrollY < this.lastScrollY) !== (this.lastScrollDirection || false);
    this.lastScrollDirection = scrollY < this.lastScrollY;
    
    // Detect scroll type (smooth = trackpad, discrete = wheel)
    const isSmooth = dt < 30; // Trackpad sends more frequent, smaller events
    
    // Send scroll event
    this._fetch('/scroll', {
      session_id: this.sessionId,
      scroll_y: scrollY,
      scroll_x: scrollX,
      scroll_depth_percent: this._getScrollDepth(),
      velocity,
      scroll_type: isSmooth ? 'trackpad' : 'wheel',
      is_reversal: isReversal,
      is_smooth: isSmooth,
    }).catch(e => this._log('Scroll send error:', e));
    
    this.lastScrollY = scrollY;
    this.lastScrollTime = now;
  }
  
  _onKeyDown(event) {
    const now = performance.now();
    
    // Don't capture actual keys for privacy - only timing and category
    const keyCategory = this._getKeyCategory(event.key);
    
    this.keystrokeBuffer.push({
      category: keyCategory,
      downTime: now,
      upTime: null,
      holdTime: null,
      flightTime: this.lastKeyUp > 0 ? now - this.lastKeyUp : null,
      isError: keyCategory === 'backspace',
    });
  }
  
  _onKeyUp(event) {
    const now = performance.now();
    const keyCategory = this._getKeyCategory(event.key);
    
    // Find matching keydown
    for (let i = this.keystrokeBuffer.length - 1; i >= 0; i--) {
      const ks = this.keystrokeBuffer[i];
      if (ks.category === keyCategory && ks.upTime === null) {
        ks.upTime = now;
        ks.holdTime = now - ks.downTime;
        break;
      }
    }
    
    this.lastKeyUp = now;
    
    // Check if we should send a sequence (e.g., on pause or after threshold)
    if (this.keystrokeBuffer.length >= 20) {
      this._sendKeystrokeSequence();
    }
  }
  
  _checkHover(event) {
    const element = event.target;
    const elementId = this._getElementId(element);
    
    if (this.hoverElement === elementId) {
      // Still on same element - count micro movements
      this.hoverMicroMovements++;
    } else {
      // Changed elements
      if (this.hoverElement) {
        this._endHover();
      }
      
      // Start new hover
      this.hoverElement = elementId;
      this.hoverStartTime = performance.now();
      this.hoverMicroMovements = 0;
    }
  }
  
  async _endHover() {
    if (!this.hoverElement) return;
    
    const duration = performance.now() - this.hoverStartTime;
    
    // Only send hovers > 200ms (meaningful attention)
    if (duration > 200) {
      await this._fetch('/cursor/hover', {
        session_id: this.sessionId,
        x: this.lastX,
        y: this.lastY,
        element_id: this.hoverElement,
        element_type: this._inferElementType(this.hoverElement),
        hover_duration_ms: Math.round(duration),
        micro_movements: this.hoverMicroMovements,
      }).catch(e => this._log('Hover send error:', e));
    }
    
    this.hoverElement = null;
    this.hoverMicroMovements = 0;
  }
  
  async _sendBatch() {
    if (this.cursorMoves.length === 0) return;
    
    const batch = this.cursorMoves.splice(0, this.batchSize);
    
    try {
      await this._fetch('/cursor/moves', {
        session_id: this.sessionId,
        moves: batch,
      });
      this._log('Batch sent:', batch.length, 'moves');
    } catch (e) {
      this._log('Batch send error:', e);
      // Put back in buffer for retry
      this.cursorMoves = batch.concat(this.cursorMoves);
    }
  }
  
  async _sendKeystrokeSequence() {
    if (this.keystrokeBuffer.length < 5) return; // Need enough data
    
    const buffer = this.keystrokeBuffer.splice(0);
    const complete = buffer.filter(k => k.holdTime !== null);
    
    if (complete.length < 3) return;
    
    // Calculate aggregate metrics
    const holdTimes = complete.map(k => k.holdTime);
    const flightTimes = complete.filter(k => k.flightTime !== null).map(k => k.flightTime);
    const errors = complete.filter(k => k.isError).length;
    
    const holdMean = this._mean(holdTimes);
    const holdStd = this._std(holdTimes);
    const flightMean = flightTimes.length > 0 ? this._mean(flightTimes) : 0;
    const flightStd = flightTimes.length > 0 ? this._std(flightTimes) : 0;
    
    // Estimate typing speed (chars per minute)
    const totalTime = complete[complete.length - 1].upTime - complete[0].downTime;
    const speed = totalTime > 0 ? (complete.length / totalTime) * 60000 : 0;
    
    await this._fetch('/keystroke/sequence', {
      session_id: this.sessionId,
      sequence_length: complete.length,
      input_type: 'text',
      hold_time_mean_ms: holdMean,
      hold_time_std_ms: holdStd,
      flight_time_mean_ms: flightMean,
      flight_time_std_ms: flightStd,
      typing_speed_cpm: speed,
      pause_count: complete.filter(k => k.flightTime > 500).length,
      burst_count: 0, // Would need more complex detection
      error_count: errors,
      error_rate: errors / complete.length,
      digraph_patterns: {}, // Would need to track patterns
    }).catch(e => this._log('Keystroke send error:', e));
  }
  
  _calculateTrajectoryMetrics(startX, startY, endX, endY, points) {
    // Calculate ideal straight line
    const totalDist = Math.sqrt((endX - startX) ** 2 + (endY - startY) ** 2);
    
    if (totalDist === 0 || points.length < 2) {
      return { auc: 0, mad: 0, xFlips: 0, yFlips: 0, initiationTime: 0 };
    }
    
    // Calculate AUC and MAD
    let areaSum = 0;
    let maxDeviation = 0;
    let xFlips = 0;
    let yFlips = 0;
    let lastXDir = 0;
    let lastYDir = 0;
    let initiationTime = 0;
    let foundMovement = false;
    
    for (let i = 1; i < points.length; i++) {
      const [px, py, t] = points[i];
      const [prevX, prevY] = points[i - 1];
      
      // Check for movement initiation
      if (!foundMovement) {
        const moveDist = Math.sqrt((px - startX) ** 2 + (py - startY) ** 2);
        if (moveDist > 5) { // 5px threshold for movement start
          initiationTime = t;
          foundMovement = true;
        }
      }
      
      // Calculate perpendicular distance from ideal line
      const t_param = ((px - startX) * (endX - startX) + (py - startY) * (endY - startY)) / (totalDist * totalDist);
      const closestX = startX + t_param * (endX - startX);
      const closestY = startY + t_param * (endY - startY);
      const deviation = Math.sqrt((px - closestX) ** 2 + (py - closestY) ** 2);
      
      areaSum += deviation;
      maxDeviation = Math.max(maxDeviation, deviation);
      
      // Count direction flips
      const xDir = Math.sign(px - prevX);
      const yDir = Math.sign(py - prevY);
      
      if (xDir !== 0 && xDir !== lastXDir && lastXDir !== 0) xFlips++;
      if (yDir !== 0 && yDir !== lastYDir && lastYDir !== 0) yFlips++;
      
      if (xDir !== 0) lastXDir = xDir;
      if (yDir !== 0) lastYDir = yDir;
    }
    
    // Normalize AUC by path length
    const auc = (areaSum / points.length) / totalDist;
    const mad = maxDeviation / totalDist;
    
    return { auc, mad, xFlips, yFlips, initiationTime };
  }
  
  _samplePoints(points, maxPoints) {
    if (points.length <= maxPoints) return points;
    
    const step = Math.ceil(points.length / maxPoints);
    return points.filter((_, i) => i % step === 0);
  }
  
  _getElementUnderCursor(event) {
    const element = event.target;
    return this._getElementId(element);
  }
  
  _getElementId(element) {
    if (!element) return null;
    return element.id ||
           element.getAttribute('data-adam-id') ||
           element.className?.split(' ')[0] ||
           element.tagName?.toLowerCase();
  }
  
  _inferElementType(elementId) {
    if (!elementId) return null;
    const lower = elementId.toLowerCase();
    if (lower.includes('button') || lower.includes('btn') || lower.includes('cta')) return 'button';
    if (lower.includes('product') || lower.includes('item')) return 'product';
    if (lower.includes('link') || lower.includes('nav')) return 'link';
    if (lower.includes('img') || lower.includes('image')) return 'image';
    return 'element';
  }
  
  _getKeyCategory(key) {
    if (key.length === 1) {
      if (/[a-zA-Z]/.test(key)) return 'letter';
      if (/[0-9]/.test(key)) return 'number';
      return 'punctuation';
    }
    if (key === 'Backspace' || key === 'Delete') return 'backspace';
    if (key === ' ') return 'space';
    if (['Shift', 'Control', 'Alt', 'Meta'].includes(key)) return 'modifier';
    return 'special';
  }
  
  _getScrollDepth() {
    const scrollY = window.scrollY;
    const viewportHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    return (scrollY + viewportHeight) / documentHeight;
  }
  
  _getDeviceInfo() {
    return {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      screenWidth: window.screen.width,
      screenHeight: window.screen.height,
      pixelRatio: window.devicePixelRatio,
    };
  }
  
  _mean(arr) {
    return arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
  }
  
  _std(arr) {
    if (arr.length < 2) return 0;
    const mean = this._mean(arr);
    const variance = arr.reduce((sum, x) => sum + (x - mean) ** 2, 0) / (arr.length - 1);
    return Math.sqrt(variance);
  }
  
  async _fetch(path, data) {
    const url = `${this.apiEndpoint}${path}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  _log(...args) {
    if (this.debug) {
      console.log('[ADAM SDK]', ...args);
    }
  }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ADAMDesktopSDK;
} else if (typeof window !== 'undefined') {
  window.ADAMDesktopSDK = ADAMDesktopSDK;
}
