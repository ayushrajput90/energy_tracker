/**
 * Centralized API & Demo Client for Renewable Energy Usage Tracker
 */
const API = {
  getToken() {
    return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
  },

  async request(endpoint, options = {}) {
    if (CONFIG.DEMO_MODE) {
      return this.handleDemoRequest(endpoint, options);
    }

    const url = `${CONFIG.API_BASE_URL}${endpoint}`;
    const token = this.getToken();

    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (response.status === 401) {
        // Unauthenticated -> clear token and redirect to login
        localStorage.removeItem('auth_token');
        sessionStorage.removeItem('auth_token');
        if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('register.html')) {
          window.location.href = 'login.html';
        }
        throw new Error('Session expired or unauthorized. Please log in.');
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || errData.message || `Request failed with status ${response.status}`);
      }

      // Check if CSV or JSON
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/csv')) {
        return await response.blob();
      }

      return await response.json();
    } catch (err) {
      console.warn(`[API Network/Server Fallback] Endpoint: ${endpoint}`, err);
      // If user is accessing statically without running backend, suggest Demo Mode
      if (err.message && (err.message.includes('Failed to fetch') || err.message.includes('NetworkError') || err.message.includes('Load failed'))) {
        UI.showToast('Backend server not connected. Operating in Demo Mode.', 'info');
        CONFIG.DEMO_MODE = true;
        localStorage.setItem('DEMO_MODE', 'true');
        return this.handleDemoRequest(endpoint, options);
      }
      throw err;
    }
  },

  // HTTP Helper shortcuts
  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    const fullEndpoint = query ? `${endpoint}?${query}` : endpoint;
    return this.request(fullEndpoint, { method: 'GET' });
  },

  post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  put(endpoint, body) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  },

  // -------------------------------------------------------------
  // DEMO MODE SIMULATOR (Standalone Browser State)
  // -------------------------------------------------------------
  handleDemoRequest(endpoint, options) {
    initDemoStorage();
    const method = options.method || 'GET';
    let records = JSON.parse(localStorage.getItem('DEMO_RECORDS') || '[]');
    let sources = JSON.parse(localStorage.getItem('DEMO_SOURCES') || '[]');
    let historyList = JSON.parse(localStorage.getItem('DEMO_CAPACITY_HISTORY') || '[]');
    let overrides = JSON.parse(localStorage.getItem('DEMO_OVERRIDES') || '[]');
    let storageTxs = JSON.parse(localStorage.getItem('DEMO_STORAGE_TXS') || '[]');
    let goals = JSON.parse(localStorage.getItem('DEMO_GOALS') || '[]');
    let activities = JSON.parse(localStorage.getItem('DEMO_ACTIVITIES') || '[]');
    let settings = JSON.parse(localStorage.getItem('DEMO_SETTINGS') || JSON.stringify(DEMO_SEED_DATA.settings));

    const tariff = parseFloat(settings.electricity_tariff || 9.0);
    const factor = parseFloat(settings.co2_emission_factor || 0.82);
    const currSym = settings.currency_symbol || '₹';

    const getStorageBalance = () => {
      let surplus = 0, consumed = 0;
      storageTxs.forEach(t => {
        if (t.transaction_type === 'SURPLUS') surplus += parseFloat(t.amount_kwh || 0);
        if (t.transaction_type === 'CONSUME') consumed += parseFloat(t.amount_kwh || 0);
      });
      return Math.max(0, surplus - consumed);
    };

    const calcRecord = (r) => {
      const gen = parseFloat(r.energy_generated_kwh || 0);
      const ren = parseFloat(r.renewable_energy_consumed_kwh || 0);
      const grid = parseFloat(r.grid_energy_consumed_kwh || 0);
      const stor = parseFloat(r.storage_used_kwh || 0);
      const surplus = Math.max(0, gen - ren);
      const cleanUtilized = ren + stor;
      const tot = cleanUtilized + grid;
      const pct = tot > 0 ? Math.min(Math.round((cleanUtilized / tot) * 1000) / 10, 100) : 0;
      const co2 = Math.round(cleanUtilized * factor * 100) / 100;
      const savings = Math.round(cleanUtilized * (parseFloat(r.electricity_tariff) || tariff) * 100) / 100;
      return {
        ...r,
        surplus_kwh: surplus,
        storage_used_kwh: stor,
        total_energy_consumed_kwh: tot,
        renewable_percentage: pct,
        co2_avoided_kg: co2,
        grid_displaced_kwh: cleanUtilized,
        estimated_savings: savings
      };
    };

    const calcSummary = (list) => {
      let tGen = 0, tRen = 0, tGrid = 0, tStor = 0, tSurp = 0, tSavings = 0;
      list.forEach(r => {
        const ren = parseFloat(r.renewable_energy_consumed_kwh || 0);
        const gen = parseFloat(r.energy_generated_kwh || 0);
        const stor = parseFloat(r.storage_used_kwh || 0);
        const recTariff = parseFloat(r.electricity_tariff) || tariff;
        tGen += gen;
        tRen += ren;
        tGrid += parseFloat(r.grid_energy_consumed_kwh || 0);
        tStor += stor;
        tSurp += Math.max(0, gen - ren);
        tSavings += (ren + stor) * recTariff;
      });
      const tClean = tRen + tStor;
      const tTot = tClean + tGrid;
      return {
        count: list.length,
        total_generated_kwh: Math.round(tGen * 100) / 100,
        total_renewable_consumed_kwh: Math.round(tRen * 100) / 100,
        total_grid_consumed_kwh: Math.round(tGrid * 100) / 100,
        total_storage_used_kwh: Math.round(tStor * 100) / 100,
        total_surplus_kwh: Math.round(tSurp * 100) / 100,
        total_consumed_kwh: Math.round(tTot * 100) / 100,
        renewable_percentage: tTot > 0 ? Math.round((tClean / tTot) * 1000) / 10 : 0,
        estimated_co2_avoided_kg: Math.round(tClean * factor * 100) / 100,
        estimated_grid_displaced_kwh: Math.round(tClean * 100) / 100,
        estimated_cost_savings: Math.round(tSavings * 100) / 100
      };
    };

    const filterRecordsByParams = (allRecs, src, timeFilter, sDate, eDate) => {
      let filtered = [...allRecs];

      if (src && src.trim() && !['all', 'all sources', 'all sources combined'].includes(src.trim().toLowerCase())) {
        filtered = filtered.filter(r => (r.renewable_source || '').toLowerCase() === src.trim().toLowerCase());
      }

      const todayStr = new Date().toISOString().split('T')[0];
      const now = new Date();

      if (sDate && eDate) {
        filtered = filtered.filter(r => r.date >= sDate && r.date <= eDate);
      } else if (sDate) {
        filtered = filtered.filter(r => r.date >= sDate);
      } else if (timeFilter) {
        const tf = timeFilter.toLowerCase().trim();
        if (tf === 'today' || tf === 'day') {
          filtered = filtered.filter(r => r.date === todayStr);
        } else if (tf === 'yesterday') {
          const yest = new Date(Date.now() - 86400000).toISOString().split('T')[0];
          filtered = filtered.filter(r => r.date === yest);
        } else if (tf === 'this_week' || tf === 'weekly' || tf === 'week') {
          const dayOfWeek = now.getDay();
          const diffToMonday = (dayOfWeek === 0 ? -6 : 1) - dayOfWeek;
          const monday = new Date(now);
          monday.setDate(now.getDate() + diffToMonday);
          const monStr = monday.toISOString().split('T')[0];
          filtered = filtered.filter(r => r.date >= monStr && r.date <= todayStr);
        } else if (tf === 'this_month' || tf === 'monthly' || tf === 'month') {
          const monthStart = todayStr.substring(0, 7) + '-01';
          filtered = filtered.filter(r => r.date >= monthStart && r.date <= todayStr);
        } else if (tf === 'this_year' || tf === 'yearly' || tf === 'year') {
          const yearStart = todayStr.substring(0, 4) + '-01-01';
          filtered = filtered.filter(r => r.date >= yearStart && r.date <= todayStr);
        }
      }

      return filtered;
    };

    const aggregateDailySeries = (recs) => {
      const dateMap = {};
      recs.forEach(r => {
        const d = r.date;
        if (!dateMap[d]) dateMap[d] = [];
        dateMap[d].push(r);
      });
      const dates = Object.keys(dateMap).sort();
      return dates.map(d => {
        const sum = calcSummary(dateMap[d]);
        return {
          date: d,
          ...sum
        };
      });
    };

    const aggregateSourceMap = (recs) => {
      const srcMap = {};
      CONFIG.RENEWABLE_SOURCES.forEach(s => {
        const sRecs = recs.filter(r => r.renewable_source === s);
        const sSum = calcSummary(sRecs);
        srcMap[s] = {
          source: s,
          record_count: sRecs.length,
          total_generated_kwh: sSum.total_generated_kwh,
          total_renewable_consumed_kwh: sSum.total_renewable_consumed_kwh,
          total_grid_consumed_kwh: sSum.total_grid_consumed_kwh,
          total_storage_used_kwh: sSum.total_storage_used_kwh,
          total_surplus_kwh: sSum.total_surplus_kwh,
          total_consumed_kwh: sSum.total_consumed_kwh,
          renewable_percentage: sSum.renewable_percentage,
          estimated_co2_avoided_kg: sSum.estimated_co2_avoided_kg,
          estimated_cost_savings: sSum.estimated_cost_savings,
          contribution_percentage: 0
        };
      });
      const totGen = Object.values(srcMap).reduce((acc, v) => acc + v.total_generated_kwh, 0);
      Object.values(srcMap).forEach(v => {
        v.contribution_percentage = totGen > 0 ? Math.round((v.total_generated_kwh / totGen) * 1000) / 10 : 0;
      });
      return srcMap;
    };

    // Auth endpoints in Demo Mode
    if (endpoint.startsWith('/auth/login') || endpoint.startsWith('/auth/register')) {
      return Promise.resolve({
        message: 'Demo Login Success',
        access_token: 'demo-jwt-token-12345',
        user: DEMO_SEED_DATA.user,
        settings: settings
      });
    }

    if (endpoint === '/auth/logout') {
      return Promise.resolve({ message: 'Demo logout success' });
    }

    if (endpoint === '/auth/me') {
      return Promise.resolve({ user: DEMO_SEED_DATA.user, settings: settings });
    }

    // Sources CRUD
    if (endpoint.startsWith('/sources')) {
      if (endpoint === '/sources' && method === 'GET') {
        const totalCap = sources.filter(s => s.active).reduce((sum, s) => sum + parseFloat(s.installed_capacity_kw || 0), 0);
        const totalExp = sources.filter(s => s.active).reduce((sum, s) => sum + parseFloat(s.expected_daily_generation_kwh || 0), 0);
        return Promise.resolve({
          sources: sources.map(s => ({
            ...s,
            history_count: historyList.filter(h => h.source_id === s.id).length
          })),
          total_installed_capacity_kw: Math.round(totalCap * 100) / 100,
          total_expected_daily_generation_kwh: Math.round(totalExp * 100) / 100,
          active_count: sources.filter(s => s.active).length,
          total_count: sources.length
        });
      }

      if (endpoint === '/sources' && method === 'POST') {
        const body = JSON.parse(options.body);
        const newSrc = {
          id: Date.now(),
          user_id: 1,
          source_type: body.source_type,
          installed_capacity_kw: parseFloat(body.installed_capacity_kw || 0),
          expected_daily_generation_kwh: parseFloat(body.expected_daily_generation_kwh || 0),
          effective_from: body.effective_from || new Date().toISOString().split('T')[0],
          active: body.active !== undefined ? body.active : true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        sources.push(newSrc);
        historyList.push({
          id: Date.now(),
          source_id: newSrc.id,
          capacity_kw: newSrc.installed_capacity_kw,
          expected_daily_generation_kwh: newSrc.expected_daily_generation_kwh,
          effective_from: newSrc.effective_from,
          effective_to: null,
          created_at: new Date().toISOString()
        });
        localStorage.setItem('DEMO_SOURCES', JSON.stringify(sources));
        localStorage.setItem('DEMO_CAPACITY_HISTORY', JSON.stringify(historyList));
        return Promise.resolve({ message: 'Source configuration saved.', source: newSrc });
      }

      const matchSrcHist = endpoint.match(/\/sources\/(\d+)\/history/);
      if (matchSrcHist) {
        const srcId = parseInt(matchSrcHist[1]);
        const src = sources.find(s => s.id === srcId);
        const hists = historyList.filter(h => h.source_id === srcId);
        return Promise.resolve({ source: src, history: hists });
      }

      const matchSrcId = endpoint.match(/\/sources\/(\d+)/);
      if (matchSrcId) {
        const srcId = parseInt(matchSrcId[1]);
        if (method === 'GET') {
          const src = sources.find(s => s.id === srcId);
          return src ? Promise.resolve({ source: src }) : Promise.reject(new Error('Source not found'));
        }
        if (method === 'PUT') {
          const body = JSON.parse(options.body);
          const idx = sources.findIndex(s => s.id === srcId);
          if (idx !== -1) {
            sources[idx] = { ...sources[idx], ...body, updated_at: new Date().toISOString() };
            localStorage.setItem('DEMO_SOURCES', JSON.stringify(sources));
            return Promise.resolve({ message: 'Source updated', source: sources[idx] });
          }
        }
        if (method === 'DELETE') {
          sources = sources.filter(s => s.id !== srcId);
          localStorage.setItem('DEMO_SOURCES', JSON.stringify(sources));
          return Promise.resolve({ message: 'Source configuration deleted.' });
        }
      }
    }

    // Generation Telemetry & Aggregation
    if (endpoint.startsWith('/generation')) {
      if (endpoint === '/generation' || endpoint.startsWith('/generation?')) {
        const urlObj = new URL('http://dummy.com' + endpoint);
        const tDate = urlObj.searchParams.get('date') || new Date().toISOString().split('T')[0];
        
        let totalAuto = 0, totalFinal = 0;
        let hasOv = false;
        const sourceBreakdown = sources.filter(s => s.active).map(s => {
          const autoKwh = parseFloat(s.expected_daily_generation_kwh || 0);
          const ov = overrides.find(o => o.source_id === s.id && o.date === tDate);
          const isOv = !!ov;
          if (isOv) hasOv = true;
          const finalKwh = isOv ? parseFloat(ov.override_generation_kwh) : autoKwh;
          totalAuto += autoKwh;
          totalFinal += finalKwh;
          return {
            source_id: s.id,
            source_type: s.source_type,
            capacity_kw: s.installed_capacity_kw,
            automatic_generation_kwh: autoKwh,
            override_generation_kwh: isOv ? parseFloat(ov.override_generation_kwh) : null,
            final_generation_kwh: finalKwh,
            is_override: isOv,
            reason: isOv ? ov.reason : ''
          };
        });

        return Promise.resolve({
          date: tDate,
          total_automatic_generation_kwh: Math.round(totalAuto * 100) / 100,
          total_final_generation_kwh: Math.round(totalFinal * 100) / 100,
          has_override: hasOv,
          sources: sourceBreakdown
        });
      }

      if (endpoint.startsWith('/generation/history')) {
        const urlObj = new URL('http://dummy.com' + endpoint);
        const srcFilter = urlObj.searchParams.get('source_type');
        const activeSources = sources.filter(s => {
          if (srcFilter && srcFilter.trim() && !['all', 'all sources'].includes(srcFilter.trim().toLowerCase())) {
            return (s.source_type || '').toLowerCase() === srcFilter.trim().toLowerCase();
          }
          return true;
        });

        const todayStr = new Date().toISOString().split('T')[0];
        const history = [];

        activeSources.forEach(s => {
          const startStr = s.effective_from || '2026-08-01';
          let cur = new Date(startStr);
          const today = new Date(todayStr);

          while (cur <= today) {
            const curStr = cur.toISOString().split('T')[0];
            const autoKwh = parseFloat(s.expected_daily_generation_kwh || 0);
            const ov = overrides.find(o => o.source_id === s.id && o.date === curStr);
            const isOv = !!ov;
            const genKwh = isOv ? parseFloat(ov.override_generation_kwh) : autoKwh;

            history.push({
              source_id: s.id,
              source_type: s.source_type,
              date: curStr,
              generated_kwh: Math.round(genKwh * 100) / 100,
              automatic_generation_kwh: Math.round(autoKwh * 100) / 100,
              status: isOv ? 'Override' : 'Auto',
              is_override: isOv,
              reason: isOv ? ov.reason : ''
            });

            cur.setDate(cur.getDate() + 1);
          }
        });

        history.sort((a, b) => (b.date > a.date ? 1 : b.date < a.date ? -1 : 0));

        return Promise.resolve({
          history: history,
          sources: activeSources,
          total_count: history.length
        });
      }

      if (endpoint.startsWith('/generation/daily') || endpoint.startsWith('/generation/weekly') || endpoint.startsWith('/generation/monthly') || endpoint.startsWith('/generation/yearly')) {
        const summary = calcSummary(records);
        return Promise.resolve({
          period: endpoint.split('/')[2].split('?')[0],
          summary: summary,
          data: records.map(calcRecord)
        });
      }

      // Overrides CRUD
      if (endpoint.startsWith('/generation/overrides')) {
        if (method === 'GET') {
          return Promise.resolve({ overrides: overrides, total_count: overrides.length });
        }
        if (method === 'POST') {
          const body = JSON.parse(options.body);
          const newOv = {
            id: Date.now(),
            user_id: 1,
            source_id: parseInt(body.source_id),
            date: body.date,
            automatic_generation_kwh: parseFloat(body.automatic_generation_kwh || 15),
            override_generation_kwh: parseFloat(body.override_generation_kwh || 0),
            reason: body.reason || '',
            created_at: new Date().toISOString()
          };
          overrides.push(newOv);
          localStorage.setItem('DEMO_OVERRIDES', JSON.stringify(overrides));
          return Promise.resolve({ message: 'Override saved.', override: newOv });
        }
        const matchOvId = endpoint.match(/\/generation\/overrides\/(\d+)/);
        if (matchOvId && method === 'DELETE') {
          const ovId = parseInt(matchOvId[1]);
          overrides = overrides.filter(o => o.id !== ovId);
          localStorage.setItem('DEMO_OVERRIDES', JSON.stringify(overrides));
          return Promise.resolve({ message: 'Override deleted. Automatic generation restored.' });
        }
      }
    }

    // Storage Endpoints
    if (endpoint.startsWith('/storage')) {
      const curBal = getStorageBalance();
      if (endpoint === '/storage' || endpoint.startsWith('/storage?')) {
        return Promise.resolve({
          available_storage_kwh: Math.round(curBal * 100) / 100,
          total_surplus_stored_kwh: Math.round(storageTxs.filter(t => t.transaction_type === 'SURPLUS').reduce((s, t) => s + t.amount_kwh, 0) * 100) / 100,
          total_storage_consumed_kwh: Math.round(storageTxs.filter(t => t.transaction_type === 'CONSUME').reduce((s, t) => s + t.amount_kwh, 0) * 100) / 100,
          transaction_count: storageTxs.length
        });
      }

      if (endpoint.startsWith('/storage/transactions')) {
        return Promise.resolve({
          available_balance_kwh: Math.round(curBal * 100) / 100,
          transactions: storageTxs,
          total_count: storageTxs.length
        });
      }

      if (endpoint === '/storage/consume' && method === 'POST') {
        const body = JSON.parse(options.body);
        const amt = parseFloat(body.amount_kwh || 0);
        if (amt > curBal) {
          return Promise.reject(new Error(`Cannot consume ${amt} kWh. Available balance is ${curBal} kWh.`));
        }
        const newTx = {
          id: Date.now(),
          user_id: 1,
          date: body.date || new Date().toISOString().split('T')[0],
          transaction_type: 'CONSUME',
          amount_kwh: amt,
          notes: body.notes || 'Consumed from battery storage',
          created_at: new Date().toISOString()
        };
        storageTxs.unshift(newTx);
        localStorage.setItem('DEMO_STORAGE_TXS', JSON.stringify(storageTxs));
        return Promise.resolve({ message: 'Storage consumed.', remaining_storage_kwh: curBal - amt, transaction: newTx });
      }
    }

    // Energy Records CRUD
    if (endpoint.startsWith('/energy')) {
      if (method === 'GET' && !endpoint.includes('/export/csv') && !endpoint.match(/\/energy\/\d+/)) {
        const urlObj = new URL('http://dummy.com' + endpoint);
        const src = urlObj.searchParams.get('source');
        const timeFilter = urlObj.searchParams.get('time_filter');
        const sDate = urlObj.searchParams.get('start_date');
        const eDate = urlObj.searchParams.get('end_date');
        const search = (urlObj.searchParams.get('search') || '').toLowerCase();

        let filtered = filterRecordsByParams(records, src, timeFilter, sDate, eDate);

        if (search) {
          filtered = filtered.filter(r => (r.renewable_source || '').toLowerCase().includes(search) || (r.notes || '').toLowerCase().includes(search));
        }

        const summary = calcSummary(filtered);
        const mapped = filtered.map(calcRecord);
        return Promise.resolve({ records: mapped, summary: summary, total_items: mapped.length });
      }

      if (method === 'POST') {
        const body = JSON.parse(options.body);
        const genVal = parseFloat(body.energy_generated_kwh || 0);
        const renVal = parseFloat(body.renewable_energy_consumed_kwh || 0);
        const gridVal = parseFloat(body.grid_energy_consumed_kwh || 0);
        const storVal = parseFloat(body.storage_used_kwh || 0);
        const surplusVal = Math.max(0, genVal - renVal);
        const curBal = getStorageBalance();

        if (storVal > curBal + surplusVal) {
          return Promise.reject(new Error(`Cannot use ${storVal} kWh from storage. Available is ${(curBal + surplusVal).toFixed(1)} kWh.`));
        }

        const newRec = {
          id: Date.now(),
          user_id: 1,
          source_id: body.source_id,
          date: body.date,
          renewable_source: body.renewable_source,
          energy_generated_kwh: genVal,
          renewable_energy_consumed_kwh: renVal,
          grid_energy_consumed_kwh: gridVal,
          storage_used_kwh: storVal,
          surplus_kwh: surplusVal,
          storage_balance_kwh: curBal + surplusVal - storVal,
          is_override: !!body.is_override,
          automatic_generation_kwh: parseFloat(body.automatic_generation_kwh || genVal),
          override_generation_kwh: body.override_generation_kwh !== undefined ? parseFloat(body.override_generation_kwh) : null,
          electricity_tariff: parseFloat(body.electricity_tariff || tariff),
          notes: body.notes || ''
        };
        records.unshift(newRec);
        localStorage.setItem('DEMO_RECORDS', JSON.stringify(records));

        // Add storage transactions
        if (surplusVal > 0) {
          storageTxs.unshift({ id: Date.now(), user_id: 1, date: body.date, transaction_type: 'SURPLUS', amount_kwh: surplusVal, notes: `Surplus from ${body.renewable_source}`, created_at: new Date().toISOString() });
        }
        if (storVal > 0) {
          storageTxs.unshift({ id: Date.now() + 1, user_id: 1, date: body.date, transaction_type: 'CONSUME', amount_kwh: storVal, notes: `Consumed on ${body.date}`, created_at: new Date().toISOString() });
        }
        localStorage.setItem('DEMO_STORAGE_TXS', JSON.stringify(storageTxs));

        return Promise.resolve({ message: 'Record saved successfully', record: calcRecord(newRec) });
      }

      const matchId = endpoint.match(/\/energy\/(\d+)/);
      if (matchId) {
        const id = parseInt(matchId[1]);
        if (method === 'GET') {
          const rec = records.find(r => r.id === id);
          return rec ? Promise.resolve({ record: calcRecord(rec) }) : Promise.reject(new Error('Record not found'));
        }
        if (method === 'PUT') {
          const body = JSON.parse(options.body);
          const idx = records.findIndex(r => r.id === id);
          if (idx !== -1) {
            records[idx] = { ...records[idx], ...body };
            localStorage.setItem('DEMO_RECORDS', JSON.stringify(records));
            return Promise.resolve({ message: 'Record updated', record: calcRecord(records[idx]) });
          }
        }
        if (method === 'DELETE') {
          records = records.filter(r => r.id !== id);
          localStorage.setItem('DEMO_RECORDS', JSON.stringify(records));
          return Promise.resolve({ message: 'Record deleted' });
        }
      }
    }

    // Analytics Endpoints in Demo Mode
    if (endpoint.startsWith('/analytics/overview')) {
      const urlObj = new URL('http://dummy.com' + endpoint);
      const src = urlObj.searchParams.get('source');
      const timeFilter = urlObj.searchParams.get('time_filter') || 'this_year';
      const sDate = urlObj.searchParams.get('start_date');
      const eDate = urlObj.searchParams.get('end_date');

      const filtered = filterRecordsByParams(records, src, timeFilter, sDate, eDate);
      const summary = calcSummary(filtered);
      const dailySeries = aggregateDailySeries(filtered);
      const sourcesData = aggregateSourceMap(filtered);

      return Promise.resolve({
        summary: summary,
        daily_series: dailySeries,
        sources_data: sourcesData,
        sources_list: Object.values(sourcesData),
        currency_symbol: currSym
      });
    }

    if (endpoint.startsWith('/analytics/sources')) {
      const urlObj = new URL('http://dummy.com' + endpoint);
      const src = urlObj.searchParams.get('source');
      const timeFilter = urlObj.searchParams.get('time_filter') || 'this_year';
      const sDate = urlObj.searchParams.get('start_date');
      const eDate = urlObj.searchParams.get('end_date');

      const filtered = filterRecordsByParams(records, src, timeFilter, sDate, eDate);
      const sourcesData = aggregateSourceMap(filtered);

      const filteredList = CONFIG.RENEWABLE_SOURCES.filter(s => (!src || ['all', 'all sources', 'all sources combined'].includes(src.toLowerCase()) || s.toLowerCase() === src.toLowerCase()));
      const labels = [];
      const generatedData = [];
      const consumedData = [];
      const co2Data = [];
      const savingsData = [];

      filteredList.forEach(s => {
        const info = sourcesData[s] || {};
        labels.push(s);
        generatedData.push(info.total_generated_kwh || 0);
        consumedData.push(info.total_renewable_consumed_kwh || 0);
        co2Data.push(info.estimated_co2_avoided_kg || 0);
        savingsData.push(info.estimated_cost_savings || 0);
      });

      return Promise.resolve({
        sources_data: sourcesData,
        table_data: filteredList.map(s => sourcesData[s]),
        currency_symbol: currSym,
        chart: {
          labels: labels,
          generated: generatedData,
          consumed: consumedData,
          co2_avoided: co2Data,
          savings: savingsData
        }
      });
    }

    if (endpoint.startsWith('/analytics/environmental')) {
      const urlObj = new URL('http://dummy.com' + endpoint);
      const src = urlObj.searchParams.get('source');
      const timeFilter = urlObj.searchParams.get('time_filter') || 'all';
      const sDate = urlObj.searchParams.get('start_date');
      const eDate = urlObj.searchParams.get('end_date');

      const filtered = filterRecordsByParams(records, src, timeFilter, sDate, eDate);
      const overall = calcSummary(filtered);

      const todayStr = new Date().toISOString().split('T')[0];
      const monthStart = todayStr.substring(0, 7) + '-01';
      const yearStart = todayStr.substring(0, 4) + '-01-01';

      const allForSource = (src && !['all', 'all sources'].includes(src.toLowerCase())) ? records.filter(r => r.renewable_source === src) : records;
      const todayRecs = allForSource.filter(r => r.date === todayStr);
      const monthRecs = allForSource.filter(r => r.date >= monthStart);
      const yearRecs = allForSource.filter(r => r.date >= yearStart);

      const todayAgg = calcSummary(todayRecs);
      const monthAgg = calcSummary(monthRecs);
      const yearAgg = calcSummary(yearRecs);

      const totalCo2 = overall.estimated_co2_avoided_kg;
      const treesEquiv = Math.round((totalCo2 / 21.77) * 10) / 10;
      const carMilesEquiv = Math.round(totalCo2 * 2.5 * 10) / 10;
      const coalLbsEquiv = Math.round(totalCo2 * 1.1 * 10) / 10;

      const dailyTrend = aggregateDailySeries(filtered);

      return Promise.resolve({
        total_co2_avoided_kg: totalCo2,
        today_co2_avoided_kg: todayAgg.estimated_co2_avoided_kg,
        monthly_co2_avoided_kg: monthAgg.estimated_co2_avoided_kg,
        yearly_co2_avoided_kg: yearAgg.estimated_co2_avoided_kg,
        renewable_percentage: overall.renewable_percentage,
        estimated_grid_displaced_kwh: overall.estimated_grid_displaced_kwh,
        emission_factor: factor,
        equivalencies: {
          trees_planted_yearly: treesEquiv,
          car_miles_displaced: carMilesEquiv,
          coal_burn_avoided_lbs: coalLbsEquiv
        },
        methodology: {
          formula: 'Estimated CO2 Avoided (kg) = Renewable Energy Consumed (kWh) × Grid Emission Factor (kg CO2/kWh)',
          factor_used: `${factor} kg CO2/kWh`,
          description: 'Calculates the greenhouse gas emissions prevented by substituting fossil-fueled grid electricity with zero-emission on-site renewable generation.'
        },
        trend: dailyTrend
      });
    }

    if (endpoint.startsWith('/analytics/savings')) {
      const urlObj = new URL('http://dummy.com' + endpoint);
      const src = urlObj.searchParams.get('source');
      const timeFilter = urlObj.searchParams.get('time_filter') || 'all';
      const sDate = urlObj.searchParams.get('start_date');
      const eDate = urlObj.searchParams.get('end_date');

      const filtered = filterRecordsByParams(records, src, timeFilter, sDate, eDate);
      const overall = calcSummary(filtered);

      const todayStr = new Date().toISOString().split('T')[0];
      const monthStart = todayStr.substring(0, 7) + '-01';
      const yearStart = todayStr.substring(0, 4) + '-01-01';

      const allForSource = (src && !['all', 'all sources'].includes(src.toLowerCase())) ? records.filter(r => r.renewable_source === src) : records;
      const todayRecs = allForSource.filter(r => r.date === todayStr);
      const monthRecs = allForSource.filter(r => r.date >= monthStart);
      const yearRecs = allForSource.filter(r => r.date >= yearStart);

      const todayAgg = calcSummary(todayRecs);
      const monthAgg = calcSummary(monthRecs);
      const yearAgg = calcSummary(yearRecs);

      const dailyTrend = aggregateDailySeries(filtered);

      return Promise.resolve({
        total_savings: overall.estimated_cost_savings,
        today_savings: todayAgg.estimated_cost_savings,
        monthly_savings: monthAgg.estimated_cost_savings,
        yearly_savings: yearAgg.estimated_cost_savings,
        renewable_consumed_kwh: overall.total_renewable_consumed_kwh,
        grid_displaced_kwh: overall.estimated_grid_displaced_kwh,
        current_tariff: tariff,
        currency_symbol: currSym,
        methodology: {
          formula: `Estimated Cost Savings = Renewable Energy Consumed (kWh) × Electricity Tariff (${currSym}/kWh)`,
          tariff_used: `${currSym}${tariff.toFixed(4)}/kWh`,
          notes: 'Actual utility bill reductions can vary based on net metering policies, tier rates, and peak load surcharges.'
        },
        trend: dailyTrend
      });
    }

    if (endpoint === '/analytics/insights') {
      return Promise.resolve({
        insights: [
          { type: 'top_source', icon: 'sun', category: 'Source Performance', title: 'Solar is your #1 Energy Producer', message: 'Solar contributed the highest share of clean power generated across all records.', badge: 'Top Contributor' },
          { type: 'milestone', icon: 'award', category: 'Efficiency', title: 'Clean Power Majority', message: 'The majority of your energy demand was covered by clean renewable sources.', badge: 'Milestone' }
        ]
      });
    }

    // Dashboard Stats
    if (endpoint.startsWith('/dashboard/stats')) {
      const urlObj = new URL('http://dummy.com' + endpoint);
      const period = urlObj.searchParams.get('period') || 'all';
      const sDate = urlObj.searchParams.get('start_date');
      const eDate = urlObj.searchParams.get('end_date');

      const filtered = filterRecordsByParams(records, null, period, sDate, eDate);
      const periodSummary = calcSummary(filtered);
      const overall = calcSummary(records);
      const today = new Date().toISOString().split('T')[0];
      const todayRecs = records.filter(r => r.date === today);
      const todaySum = calcSummary(todayRecs);
      const curBal = getStorageBalance();

      const sourcesData = aggregateSourceMap(filtered);

      const totalCap = sources.filter(s => s.active).reduce((sum, s) => sum + parseFloat(s.installed_capacity_kw || 0), 0);
      const totalExp = sources.filter(s => s.active).reduce((sum, s) => sum + parseFloat(s.expected_daily_generation_kwh || 0), 0);

      const dailySeries = aggregateDailySeries(filtered);
      const chartLabels = dailySeries.map(d => d.date);
      const chartGen = dailySeries.map(d => d.total_generated_kwh);
      const chartCon = dailySeries.map(d => d.total_renewable_consumed_kwh);

      return Promise.resolve({
        overall: overall,
        period_summary: periodSummary,
        today: todaySum,
        this_month: periodSummary,
        selected_period: period,
        sources_summary: Object.values(sourcesData),
        chart_data: {
          labels: chartLabels,
          generated: chartGen,
          consumed: chartCon,
          period: period
        },
        active_goals: goals.map(g => ({
          id: g.id,
          goal_type: g.goal_type,
          target_value: g.target_value,
          current_value: 125.0,
          completion_percentage: 62.5,
          end_date: g.end_date,
          description: g.description
        })),
        active_goals_count: goals.length,
        storage: {
          available_kwh: Math.round(curBal * 100) / 100,
          today_storage_used_kwh: todaySum.total_storage_used_kwh,
          today_surplus_kwh: todaySum.total_surplus_kwh
        },
        telemetry_today: {
          date: today,
          total_automatic_generation_kwh: totalExp,
          total_final_generation_kwh: totalExp,
          has_override: false,
          sources: sources.filter(s => s.active).map(s => ({
            source_id: s.id,
            source_type: s.source_type,
            capacity_kw: s.installed_capacity_kw,
            automatic_generation_kwh: s.expected_daily_generation_kwh,
            override_generation_kwh: null,
            final_generation_kwh: s.expected_daily_generation_kwh,
            is_override: false,
            reason: ''
          }))
        },
        system: {
          installed_capacity_kw: totalCap,
          expected_daily_generation_kwh: totalExp,
          active_sources_count: sources.filter(s => s.active).length,
          total_sources_count: sources.length,
          currency_code: settings.currency_code || 'INR',
          currency_symbol: currSym,
          tariff: tariff,
          emission_factor: factor
        }
      });
    }

    if (endpoint === '/dashboard/recent') {
      return Promise.resolve({
        recent_records: records.slice(0, 5).map(calcRecord),
        recent_activities: activities.slice(0, 5),
        top_insights: [
          { type: 'top_source', icon: 'sun', category: 'Source Performance', title: 'Solar is your #1 Energy Producer', message: 'Solar contributed over 45% of all clean power generated this month.', badge: 'Top Contributor' },
          { type: 'milestone', icon: 'award', category: 'Efficiency', title: 'Clean Power Majority (74.2%)', message: 'The majority of your energy demand was covered by clean renewable sources.', badge: 'Milestone' }
        ]
      });
    }

    if (endpoint === '/settings') {
      if (method === 'GET') {
        return Promise.resolve({ user: DEMO_SEED_DATA.user, settings: settings });
      }
      if (method === 'PUT') {
        const body = JSON.parse(options.body);
        settings = { ...settings, ...body };
        localStorage.setItem('DEMO_SETTINGS', JSON.stringify(settings));
        return Promise.resolve({ message: 'Settings updated.', settings: settings });
      }
    }

    // Default fallback
    return Promise.resolve({ status: 'ok', data: [] });
  }
};

// Explicitly bind to global window
if (typeof window !== 'undefined') {
  window.API = API;
}
