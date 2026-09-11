// VPP Dashboard JavaScript
const API_BASE_URL = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/api/admin/ws";
let currentSimulationData = null;
let currentHouseId = null;
let currentEditDeviceId = null;
let websocket = null;

// Initialize app
document.addEventListener("DOMContentLoaded", () => {
  checkAPIStatusOnce(); // Check once at startup, no polling
  loadHouses();
  loadConfig();
  connectWebSocket();
});

// WebSocket connection for live updates
function connectWebSocket() {
  try {
    websocket = new WebSocket(WS_URL);

    websocket.onopen = () => {
      console.log("WebSocket connected");
      showNotification("Live updates connected", "success");
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    websocket.onclose = () => {
      console.log("WebSocket disconnected, reconnecting in 5s...");
      setTimeout(connectWebSocket, 5000);
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  } catch (error) {
    console.error("Failed to connect WebSocket:", error);
    setTimeout(connectWebSocket, 5000);
  }
}

function handleWebSocketMessage(message) {
  if (message.type === "step") {
    // Update header simulation time from WebSocket data
    const data = message.data;
    if (data.sim_clock) {
      updateHeaderSimTime(data.sim_clock);
    }

    // Update house details if a house is selected (live update without full refresh)
    if (currentHouseId && data.houses) {
      const houseData = data.houses.find(
        (h) => h.id === parseInt(currentHouseId)
      );
      if (houseData) {
        updateHouseDetailsLive(houseData);
      }
    }

    // Update VPP stats
    if (data.P_total_pv_kw !== undefined) {
      updateVPPStatsLive(data);
    }
  } else if (message.type === "status") {
    console.log("Simulation status:", message.status);
  }
}

// API Status Check - runs once at startup
async function checkAPIStatusOnce() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data = await response.json();

    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");

    if (response.ok) {
      statusDot.className = "status-dot online";
      statusText.textContent = "API Online";

      if (data.vpp_initialized) {
        loadVPPStats();
        // Update header simulation time
        if (data.sim_clock) {
          updateHeaderSimTime(data.sim_clock);
        }
      }
    }
  } catch (error) {
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    statusDot.className = "status-dot offline";
    statusText.textContent = "API Offline";
  }
}

// Update header simulation time display
function updateHeaderSimTime(simClock) {
  const timeEl = document.getElementById("headerSimTime");
  const dateEl = document.getElementById("headerSimDate");

  if (simClock.sim_time && timeEl) {
    timeEl.textContent = simClock.sim_time;
  }

  if (simClock.sim_datetime && dateEl) {
    const dt = new Date(simClock.sim_datetime);
    const dateStr = dt.toLocaleDateString("ro-RO", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    dateEl.textContent = dateStr;
  }
}

// Initialize VPP
async function initializeVPP() {
  showLoading("Initializing VPP with 10 houses (OPCOM prices)...");

  try {
    const response = await fetch(`${API_BASE_URL}/api/sim/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        num_houses: 10,
        houses_with_battery_ratio: 0.8,
        use_opcom_prices: true,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      const priceInfo =
        data.price_source === "OPCOM" ? " using OPCOM prices! 📊" : "!";
      showToast(`VPP initialized successfully${priceInfo}`, "success");
      loadVPPStats();
      loadHouses();
    } else {
      showToast("Failed to initialize VPP", "error");
    }
  } catch (error) {
    showToast("Error: " + error.message, "error");
  } finally {
    hideLoading();
  }
}

// Load VPP Stats
async function loadVPPStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/vpp/stats`);
    const data = await response.json();

    document.getElementById("totalHouses").textContent =
      data.total_houses || "-";
    document.getElementById("housesWithBattery").textContent =
      data.houses_with_battery || "-";
    document.getElementById("totalPvCapacity").textContent =
      data.total_pv_capacity_kw?.toFixed(0) || "-";
    document.getElementById("batteryCapacity").textContent =
      data.total_battery_capacity_kwh?.toFixed(0) || "-";
  } catch (error) {
    console.error("Failed to load VPP stats:", error);
  }
}

// Simulate One Hour
async function simulateOneHour() {
  showLoading("Simulating one hour...");

  try {
    const response = await fetch(`${API_BASE_URL}/api/sim/step`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    const data = await response.json();

    if (response.ok) {
      currentSimulationData = data;
      showToast(`Hour ${data.hour} simulated successfully!`, "success");
      displayEnergyFlow(data);
      displaySimulationResults(data);
      loadVPPStats();
    } else {
      showToast("Failed to simulate hour", "error");
    }
  } catch (error) {
    showToast("Error: " + error.message, "error");
  } finally {
    hideLoading();
  }
}

// Simulate Full Day
async function simulateFullDay() {
  showLoading("Simulating 24 hours... This may take a moment...");

  try {
    const response = await fetch(`${API_BASE_URL}/api/sim/day`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    const data = await response.json();

    if (response.ok) {
      showToast("24-hour simulation completed!", "success");
      displayDaySummary(data);
      display24HourChart(data.hourly_results);
      loadVPPStats();
    } else {
      showToast("Failed to simulate day", "error");
    }
  } catch (error) {
    showToast("Error: " + error.message, "error");
  } finally {
    hideLoading();
  }
}

// Reset Simulation
async function resetSimulation() {
  if (!confirm("Are you sure you want to reset the simulation?")) return;

  showLoading("Resetting simulation...");

  try {
    const response = await fetch(`${API_BASE_URL}/api/sim/reset`, {
      method: "POST",
    });

    const data = await response.json();

    if (response.ok) {
      showToast("Simulation reset successfully!", "success");
      document.getElementById("energyFlowContent").innerHTML =
        '<p class="placeholder">Run a simulation step to see energy flow data</p>';
      document.getElementById("simulationResults").innerHTML =
        '<p class="placeholder">No simulation data yet</p>';
      document.getElementById("chartContainer").innerHTML =
        '<p class="placeholder">Run a 24-hour simulation to see charts</p>';
      loadVPPStats();
    } else {
      showToast("Failed to reset simulation", "error");
    }
  } catch (error) {
    showToast("Error: " + error.message, "error");
  } finally {
    hideLoading();
  }
}

// Display Energy Flow
function displayEnergyFlow(data) {
  const html = `
        <div class="energy-metrics">
            <div class="metric" style="border-color: #f59e0b;">
                <div class="metric-label">☀️ Total PV Production</div>
                <div class="metric-value">${data.P_total_pv_kw.toFixed(
                  2
                )} <span class="metric-unit">kW</span></div>
            </div>
            <div class="metric" style="border-color: #ef4444;">
                <div class="metric-label">⚡ Total Load</div>
                <div class="metric-value">${data.P_total_load_kw.toFixed(
                  2
                )} <span class="metric-unit">kW</span></div>
            </div>
            <div class="metric" style="border-color: #10b981;">
                <div class="metric-label">📥 Grid Import</div>
                <div class="metric-value">${data.P_grid_import_kw.toFixed(
                  2
                )} <span class="metric-unit">kW</span></div>
            </div>
            <div class="metric" style="border-color: #06b6d4;">
                <div class="metric-label">📤 Grid Export</div>
                <div class="metric-value">${data.P_grid_export_kw.toFixed(
                  2
                )} <span class="metric-unit">kW</span></div>
            </div>
            <div class="metric" style="border-color: #8b5cf6;">
                <div class="metric-label">🔄 Internal Trading</div>
                <div class="metric-value">${data.P_internal_traded_kw.toFixed(
                  2
                )} <span class="metric-unit">kW</span></div>
            </div>
            <div class="metric" style="border-color: #ec4899;">
                <div class="metric-label">🔋 Battery SOC</div>
                <div class="metric-value">${data.avg_battery_soc_percent.toFixed(
                  1
                )} <span class="metric-unit">%</span></div>
            </div>
        </div>
        <div style="margin-top: 20px; padding: 16px; background: #f8fafc; border-radius: 8px;">
            <strong>Neighborhood State:</strong> 
            <span style="color: ${
              data.neighborhood_state === "consum ridicat"
                ? "#ef4444"
                : "#10b981"
            }; font-weight: 600;">
                ${data.neighborhood_state}
            </span>
            <br>
            <strong>Price:</strong> ${data.price_per_kwh.toFixed(4)} EUR/kWh
            <br>
            <strong>Hour:</strong> ${data.hour}:00
        </div>
    `;

  document.getElementById("energyFlowContent").innerHTML = html;
}

// Display Simulation Results
function displaySimulationResults(data) {
  const html = `
        <div style="display: grid; gap: 16px;">
            <div style="padding: 16px; background: #f8fafc; border-radius: 8px;">
                <h3 style="margin-bottom: 12px;">⚡ Energy Balance</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;">
                    <div>
                        <div style="font-size: 12px; color: #64748b;">Net Consumption</div>
                        <div style="font-size: 20px; font-weight: 600;">${data.consum_net_kw.toFixed(
                          2
                        )} kW</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #64748b;">Curtailment</div>
                        <div style="font-size: 20px; font-weight: 600;">${data.P_curtailment_total_kw.toFixed(
                          2
                        )} kW</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #64748b;">Internal Trades</div>
                        <div style="font-size: 20px; font-weight: 600;">${
                          data.internal_trades_count
                        }</div>
                    </div>
                </div>
            </div>
            ${
              data.internal_trades && data.internal_trades.length > 0
                ? `
                <div style="padding: 16px; background: #f8fafc; border-radius: 8px;">
                    <h3 style="margin-bottom: 12px;">🔄 Internal Trades (Sample)</h3>
                    <div style="max-height: 200px; overflow-y: auto;">
                        ${data.internal_trades
                          .slice(0, 5)
                          .map(
                            (trade) => `
                            <div style="padding: 8px; background: white; border-radius: 6px; margin-bottom: 6px; font-size: 12px;">
                                House #${trade.from_house_id} → House #${
                              trade.to_house_id
                            }: 
                                <strong>${trade.power_kw.toFixed(
                                  2
                                )} kW</strong> @ ${trade.price_per_kwh.toFixed(
                              4
                            )} EUR/kWh
                            </div>
                        `
                          )
                          .join("")}
                        ${
                          data.internal_trades.length > 5
                            ? `<div style="text-align: center; color: #64748b; font-size: 12px; margin-top: 8px;">+ ${
                                data.internal_trades.length - 5
                              } more trades</div>`
                            : ""
                        }
                    </div>
                </div>
            `
                : ""
            }
        </div>
    `;

  document.getElementById("simulationResults").innerHTML = html;
}

// Display Day Summary
function displayDaySummary(data) {
  const summary = data.summary;
  const html = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px;">
            <div style="padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px;">
                <div style="font-size: 12px; opacity: 0.9;">Total Consumed</div>
                <div style="font-size: 24px; font-weight: 700;">${summary.total_energy_consumed_kwh.toFixed(
                  0
                )} kWh</div>
            </div>
            <div style="padding: 16px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px;">
                <div style="font-size: 12px; opacity: 0.9;">Total Produced</div>
                <div style="font-size: 24px; font-weight: 700;">${summary.total_energy_produced_kwh.toFixed(
                  0
                )} kWh</div>
            </div>
            <div style="padding: 16px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px;">
                <div style="font-size: 12px; opacity: 0.9;">Grid Import</div>
                <div style="font-size: 24px; font-weight: 700;">${summary.total_grid_import_kwh.toFixed(
                  0
                )} kWh</div>
            </div>
            <div style="padding: 16px; background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; border-radius: 8px;">
                <div style="font-size: 12px; opacity: 0.9;">Grid Export</div>
                <div style="font-size: 24px; font-weight: 700;">${summary.total_grid_export_kwh.toFixed(
                  0
                )} kWh</div>
            </div>
            <div style="padding: 16px; background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; border-radius: 8px;">
                <div style="font-size: 12px; opacity: 0.9;">Internal Trading</div>
                <div style="font-size: 24px; font-weight: 700;">${summary.total_internal_trading_kwh.toFixed(
                  0
                )} kWh</div>
            </div>
            <div style="padding: 16px; background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); color: white; border-radius: 8px;">
                <div style="font-size: 12px; opacity: 0.9;">Curtailment</div>
                <div style="font-size: 24px; font-weight: 700;">${summary.total_curtailment_kwh.toFixed(
                  0
                )} kWh</div>
            </div>
        </div>
    `;

  document.getElementById("simulationResults").innerHTML = html;
}

// Display 24-Hour Chart
function display24HourChart(hourlyResults) {
  if (!hourlyResults || hourlyResults.length === 0) return;

  const maxPV = Math.max(...hourlyResults.map((h) => h.P_total_pv_kw));
  const maxLoad = Math.max(...hourlyResults.map((h) => h.P_total_load_kw));
  const maxValue = Math.max(maxPV, maxLoad);

  const html = `
        <div style="margin-bottom: 20px;">
            <h3 style="margin-bottom: 12px;">Production vs Consumption</h3>
            <div class="simple-chart">
                ${hourlyResults
                  .map(
                    (hour, index) => `
                    <div class="chart-bar" 
                         style="height: ${
                           (hour.P_total_pv_kw / maxValue) * 100
                         }%; background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);"
                         title="Hour ${hour.hour}: ${hour.P_total_pv_kw.toFixed(
                      2
                    )} kW PV">
                        ${
                          index % 3 === 0
                            ? `<div class="chart-bar-label">${hour.hour}h</div>`
                            : ""
                        }
                    </div>
                `
                  )
                  .join("")}
            </div>
            <div style="text-align: center; margin-top: 8px; color: #f59e0b; font-weight: 600;">☀️ PV Production</div>
        </div>
        
        <div>
            <div class="simple-chart">
                ${hourlyResults
                  .map(
                    (hour) => `
                    <div class="chart-bar" 
                         style="height: ${
                           (hour.P_total_load_kw / maxValue) * 100
                         }%; background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%);"
                         title="Hour ${
                           hour.hour
                         }: ${hour.P_total_load_kw.toFixed(2)} kW Load">
                    </div>
                `
                  )
                  .join("")}
            </div>
            <div style="text-align: center; margin-top: 8px; color: #ef4444; font-weight: 600;">⚡ Total Load</div>
        </div>
    `;

  document.getElementById("chartContainer").innerHTML = html;
}

// Load Houses
async function loadHouses() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/houses`);
    const houses = await response.json();

    const select = document.getElementById("houseSelect");
    select.innerHTML = '<option value="">-- Select a house --</option>';

    houses.forEach((house) => {
      const option = document.createElement("option");
      option.value = house.id;
      option.textContent = `House #${house.id} (${house.mode}, ${
        house.has_battery ? "Battery" : "No Battery"
      })`;
      select.appendChild(option);
    });
  } catch (error) {
    console.error("Failed to load houses:", error);
  }
}

// Load House Details
async function loadHouseDetails() {
  const houseId = document.getElementById("houseSelect").value;
  if (!houseId) {
    document.getElementById("houseDetails").innerHTML =
      '<p class="placeholder">Select a house to view details</p>';
    return;
  }

  currentHouseId = houseId;
  showLoading("Loading house details...");

  try {
    const response = await fetch(`${API_BASE_URL}/api/houses/${houseId}`);
    const house = await response.json();

    displayHouseDetails(house);
  } catch (error) {
    showToast("Failed to load house details", "error");
    document.getElementById("houseDetails").innerHTML =
      '<p class="placeholder">Failed to load house details</p>';
  } finally {
    hideLoading();
  }
}

// Display House Details
function displayHouseDetails(house) {
  const html = `
        <div class="house-info">
            <h3>🏠 House #${house.id}</h3>
            <div class="house-info-grid">
                <div class="house-info-item">
                    <div class="house-info-label">Mode</div>
                    <div class="house-info-value">${house.mode}</div>
                </div>
                <div class="house-info-item">
                    <div class="house-info-label">PV Capacity</div>
                    <div class="house-info-value">${
                      house.pv_capacity_kw
                    } kW</div>
                </div>
                <div class="house-info-item">
                    <div class="house-info-label">Critical Load</div>
                    <div class="house-info-value">${house.L_crit_kw.toFixed(
                      3
                    )} kW</div>
                </div>
                <div class="house-info-item">
                    <div class="house-info-label">Non-Critical Load</div>
                    <div class="house-info-value">${house.L_noncrit_kw.toFixed(
                      3
                    )} kW</div>
                </div>
            </div>
        </div>
        
        ${
          house.battery
            ? `
            <div class="house-info" style="margin-top: 20px;">
                <h3>🔋 Battery Status</h3>
                <div class="house-info-grid">
                    <div class="house-info-item">
                        <div class="house-info-label">Capacity</div>
                        <div class="house-info-value">${
                          house.battery.capacity_kwh
                        } kWh</div>
                    </div>
                    <div class="house-info-item">
                        <div class="house-info-label">Current SOC</div>
                        <div class="house-info-value">${house.battery.soc_kwh.toFixed(
                          2
                        )} kWh</div>
                    </div>
                    <div class="house-info-item" style="border-color: ${
                      house.battery.soc_percent > 80
                        ? "#10b981"
                        : house.battery.soc_percent > 30
                        ? "#f59e0b"
                        : "#ef4444"
                    };">
                        <div class="house-info-label">SOC Percentage</div>
                        <div class="house-info-value">${house.battery.soc_percent.toFixed(
                          1
                        )}%</div>
                    </div>
                    <div class="house-info-item">
                        <div class="house-info-label">Max Charge Power</div>
                        <div class="house-info-value">${
                          house.battery.p_ch_max_kw
                        } kW</div>
                    </div>
                </div>
            </div>
        `
            : ""
        }
        
        <div class="house-info" style="margin-top: 20px;" id="energyBalanceSection">
            <h3>⚡ Energy Balance (Live)</h3>
            <div class="house-info-grid">
                <div class="house-info-item" style="border-color: #f59e0b;">
                    <div class="house-info-label">PV Production</div>
                    <div class="house-info-value">${(
                      house.pv_prod_kw || 0
                    ).toFixed(3)} kW</div>
                </div>
                <div class="house-info-item" style="border-color: #ef4444;">
                    <div class="house-info-label">Total Load</div>
                    <div class="house-info-value">${(
                      house.L_total_kw || house.L_crit_kw + house.L_noncrit_kw
                    ).toFixed(3)} kW</div>
                </div>
                <div class="house-info-item" style="border-color: ${
                  (house.pv_prod_kw || 0) >=
                  (house.L_total_kw || house.L_crit_kw + house.L_noncrit_kw)
                    ? "#10b981"
                    : "#ef4444"
                };">
                    <div class="house-info-label">Balance</div>
                    <div class="house-info-value">${(
                      (house.pv_prod_kw || 0) -
                      (house.L_total_kw || house.L_crit_kw + house.L_noncrit_kw)
                    ).toFixed(3)} kW</div>
                </div>
                <div class="house-info-item">
                    <div class="house-info-label">Status</div>
                    <div class="house-info-value" style="color: ${
                      (house.pv_prod_kw || 0) >=
                      (house.L_total_kw || house.L_crit_kw + house.L_noncrit_kw)
                        ? "#10b981"
                        : "#ef4444"
                    };">${
    (house.pv_prod_kw || 0) >=
    (house.L_total_kw || house.L_crit_kw + house.L_noncrit_kw)
      ? "☀️ Surplus"
      : "⚡ Deficit"
  }</div>
                </div>
            </div>
        </div>
        
        <div class="mode-toggle">
            <h3>⚙️ Change Mode</h3>
            <div class="mode-buttons">
                <button class="mode-btn ${
                  house.mode === "Eco" ? "active" : ""
                }" onclick="changeHouseMode('Eco')">
                    🌱 Eco Mode
                </button>
                <button class="mode-btn ${
                  house.mode === "Profit" ? "active" : ""
                }" onclick="changeHouseMode('Profit')">
                    💰 Profit Mode
                </button>
            </div>
        </div>
        
        <div class="devices-list">
            <h3>🔌 Devices</h3>
            ${house.devices
              .map(
                (device) => `
                <div class="device-item">
                    <div class="device-info">
                        <div class="device-icon">${getDeviceIcon(
                          device.name
                        )}</div>
                        <div class="device-details">
                            <div class="device-name">${device.name}</div>
                            <div class="device-power">${device.power_w}W ${
                  device.critical ? "(Critical)" : ""
                }</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <button class="btn btn-sm" onclick="openEditModal(${
                          device.id
                        })" style="padding: 6px 12px; font-size: 12px;">
                            ✏️ Edit
                        </button>
                        <span class="device-status ${
                          device.status_on ? "on" : "off"
                        }">
                            ${device.status_on ? "ON" : "OFF"}
                        </span>
                        ${
                          !device.critical
                            ? `
                            <div class="toggle-switch ${
                              device.status_on ? "active" : ""
                            }" 
                                 onclick="toggleDevice(${device.id})">
                            </div>
                        `
                            : '<span style="font-size: 12px; color: #64748b;">Always On</span>'
                        }
                    </div>
                </div>
            `
              )
              .join("")}
        </div>
    `;

  document.getElementById("houseDetails").innerHTML = html;
}

// Change House Mode
async function changeHouseMode(mode) {
  if (!currentHouseId) return;

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/houses/${currentHouseId}/mode`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      }
    );

    if (response.ok) {
      showToast(`Mode changed to ${mode}`, "success");
      loadHouseDetails();
    } else {
      showToast("Failed to change mode", "error");
    }
  } catch (error) {
    showToast("Error: " + error.message, "error");
  }
}

// Toggle Device
async function toggleDevice(deviceId) {
  if (!currentHouseId) return;

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/houses/${currentHouseId}/devices/${deviceId}/toggle`,
      {
        method: "POST",
      }
    );

    if (response.ok) {
      showToast("Device toggled", "success");
      loadHouseDetails();
    } else {
      showToast("Failed to toggle device", "error");
    }
  } catch (error) {
    showToast("Error: " + error.message, "error");
  }
}

// Get Device Icon
function getDeviceIcon(name) {
  const icons = {
    Frigider: "❄️",
    Router: "📡",
    TV: "📺",
    "Mașină spălat": "🌀",
    Iluminat: "💡",
  };
  return icons[name] || "🔌";
}

// Show Toast
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const icons = {
    success: "✅",
    error: "❌",
    warning: "⚠️",
    info: "ℹ️",
  };

  toast.innerHTML = `
        <div class="toast-icon">${icons[type]}</div>
        <div class="toast-message">${message}</div>
    `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideIn 0.3s ease reverse";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Show Loading
function showLoading(text = "Loading...") {
  document.getElementById("loadingText").textContent = text;
  document.getElementById("loadingOverlay").style.display = "flex";
}

// Hide Loading
function hideLoading() {
  document.getElementById("loadingOverlay").style.display = "none";
}

// Open Edit Modal
async function openEditModal(deviceId) {
  if (!currentHouseId) return;

  currentEditDeviceId = deviceId;

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/houses/${currentHouseId}`
    );
    const house = await response.json();

    const device = house.devices.find((d) => d.id === deviceId);
    if (!device) {
      showToast("Device not found", "error");
      return;
    }

    // Populate form
    document.getElementById("editDeviceName").value = device.name;
    document.getElementById("editDevicePower").value = device.power_w;
    document.getElementById("editDeviceCritical").checked = device.critical;
    document.getElementById("editDeviceStatus").checked = device.status_on;

    // Show modal
    document.getElementById("editDeviceModal").style.display = "flex";
  } catch (error) {
    showToast("Error loading device data", "error");
  }
}

// Close Edit Modal
function closeEditModal() {
  document.getElementById("editDeviceModal").style.display = "none";
  currentEditDeviceId = null;
}

// Save Device Changes
async function saveDeviceChanges() {
  if (!currentHouseId || !currentEditDeviceId) return;

  const name = document.getElementById("editDeviceName").value.trim();
  const power_w = parseFloat(document.getElementById("editDevicePower").value);
  const critical = document.getElementById("editDeviceCritical").checked;
  const status_on = document.getElementById("editDeviceStatus").checked;

  if (!name || !power_w || power_w <= 0) {
    showToast("Please fill all fields correctly", "error");
    return;
  }

  showLoading("Updating device...");

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/houses/${currentHouseId}/devices/${currentEditDeviceId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, power_w, critical, status_on }),
      }
    );

    if (response.ok) {
      showToast("Device updated successfully!", "success");
      closeEditModal();
      loadHouseDetails();
    } else {
      const error = await response.json();
      showToast(
        "Failed to update device: " + (error.detail || "Unknown error"),
        "error"
      );
    }
  } catch (error) {
    showToast("Error: " + error.message, "error");
  } finally {
    hideLoading();
  }
}

// Close modal on background click
document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("editDeviceModal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        closeEditModal();
      }
    });
  }

  const priceModal = document.getElementById("priceModal");
  if (priceModal) {
    priceModal.addEventListener("click", (e) => {
      if (e.target === priceModal) {
        closePriceModal();
      }
    });
  }
});

// Price Modal Functions
async function showPriceModal() {
  const modal = document.getElementById("priceModal");
  modal.style.display = "flex";

  // Reset content to loading state
  document.getElementById("priceModalContent").innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <div class="spinner" style="margin: 0 auto;"></div>
            <p style="margin-top: 16px; color: #64748b;">Loading prices...</p>
        </div>
    `;

  try {
    const response = await fetch(`${API_BASE_URL}/api/sim/opcom-prices`);

    if (!response.ok) {
      throw new Error("Failed to fetch prices");
    }

    const result = await response.json();
    const data = result.data;

    displayPriceData(data);
  } catch (error) {
    document.getElementById("priceModalContent").innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                <h3 style="color: #ef4444; margin-bottom: 8px;">Failed to Load Prices</h3>
                <p style="color: #64748b;">${error.message}</p>
                <p style="color: #64748b; font-size: 12px; margin-top: 12px;">
                    Note: OPCOM data may not be available for today yet, or there might be a network issue.
                </p>
            </div>
        `;
  }
}

function closePriceModal() {
  document.getElementById("priceModal").style.display = "none";
}

function displayPriceData(data) {
  const maxPrice = Math.max(...data.prices_lei_mwh);
  const minPrice = Math.min(...data.prices_lei_mwh);

  const html = `
        <div style="margin-bottom: 24px;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 20px;">
                <div style="padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9;">Average Price</div>
                    <div style="font-size: 24px; font-weight: 700;">${data.avg_price.toFixed(
                      2
                    )}</div>
                    <div style="font-size: 11px; opacity: 0.8;">lei/MWh</div>
                </div>
                <div style="padding: 16px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9;">Max Price</div>
                    <div style="font-size: 24px; font-weight: 700;">${maxPrice.toFixed(
                      2
                    )}</div>
                    <div style="font-size: 11px; opacity: 0.8;">lei/MWh</div>
                </div>
                <div style="padding: 16px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9;">Min Price</div>
                    <div style="font-size: 24px; font-weight: 700;">${minPrice.toFixed(
                      2
                    )}</div>
                    <div style="font-size: 11px; opacity: 0.8;">lei/MWh</div>
                </div>
            </div>
            
            <div style="padding: 16px; background: #f8fafc; border-radius: 8px; margin-bottom: 20px;">
                <div style="font-size: 14px; color: #64748b; margin-bottom: 8px;">
                    <strong>Date:</strong> ${data.date}
                </div>
                <div style="font-size: 14px; color: #64748b; margin-bottom: 8px;">
                    <strong>Resolution:</strong> ${
                      data.resolution
                    } (Hourly intervals)
                </div>
                <div style="font-size: 14px; color: #64748b;">
                    <strong>Source:</strong> OPCOM (Piața pentru Ziua Următoare)
                </div>
            </div>
        </div>
        
        <h4 style="margin-bottom: 16px;">📊 Hourly Prices Chart</h4>
        <div class="simple-chart" style="height: 250px; margin-bottom: 24px;">
            ${data.prices_lei_mwh
              .map(
                (price, hour) => `
                <div class="chart-bar" 
                     style="height: ${(price / maxPrice) * 100}%; 
                            background: ${getPriceColor(
                              price,
                              minPrice,
                              maxPrice
                            )};"
                     title="Hour ${hour}: ${price.toFixed(2)} lei/MWh">
                    ${
                      hour % 3 === 0
                        ? `<div class="chart-bar-label">${hour}h</div>`
                        : ""
                    }
                </div>
            `
              )
              .join("")}
        </div>
        
        <h4 style="margin-bottom: 16px;">📋 Detailed Prices</h4>
        <div style="max-height: 300px; overflow-y: auto; border: 2px solid #e5e7eb; border-radius: 8px;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead style="position: sticky; top: 0; background: #f1f5f9; z-index: 1;">
                    <tr>
                        <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb;">Hour</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb;">lei/MWh</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb;">lei/kWh</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.prices_lei_mwh
                      .map((priceLei, hour) => {
                        const priceKwh = data.prices_lei_kwh[hour];
                        const isMin = priceLei === minPrice;
                        const isMax = priceLei === maxPrice;
                        return `
                            <tr style="background: ${
                              hour % 2 === 0 ? "white" : "#f8fafc"
                            };">
                                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">
                                    <strong>${hour
                                      .toString()
                                      .padStart(2, "0")}:00 - ${(hour + 1)
                          .toString()
                          .padStart(2, "0")}:00</strong>
                                </td>
                                <td style="padding: 10px; text-align: right; border-bottom: 1px solid #e5e7eb; font-weight: 600; color: ${
                                  isMax
                                    ? "#ef4444"
                                    : isMin
                                    ? "#10b981"
                                    : "#1e293b"
                                };">
                                    ${priceLei.toFixed(2)} ${
                          isMax ? "🔴" : isMin ? "🟢" : ""
                        }
                                </td>
                                <td style="padding: 10px; text-align: right; border-bottom: 1px solid #e5e7eb; color: #64748b;">
                                    ${priceKwh.toFixed(4)}
                                </td>
                            </tr>
                        `;
                      })
                      .join("")}
                </tbody>
            </table>
        </div>
        
        <div style="margin-top: 16px; padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 8px; font-size: 13px;">
            <strong>💡 Tip:</strong> When initializing the VPP, enable "Use OPCOM Prices" to simulate with real market data instead of generated prices.
        </div>
    `;

  document.getElementById("priceModalContent").innerHTML = html;
}

function getPriceColor(price, minPrice, maxPrice) {
  const range = maxPrice - minPrice;
  const normalized = (price - minPrice) / range;

  if (normalized < 0.33) {
    return "linear-gradient(180deg, #10b981 0%, #059669 100%)"; // Green (low)
  } else if (normalized < 0.66) {
    return "linear-gradient(180deg, #f59e0b 0%, #d97706 100%)"; // Orange (medium)
  } else {
    return "linear-gradient(180deg, #ef4444 0%, #dc2626 100%)"; // Red (high)
  }
}

// Configuration Management
let currentConfig = null;
let currentConfigTab = "prices";

async function loadConfig() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/config`);
    const config = await response.json();
    currentConfig = config;
    showConfigTab(currentConfigTab);
  } catch (error) {
    console.error("Failed to load config:", error);
  }
}

function showConfigTab(tab, clickedElement) {
  currentConfigTab = tab;

  // Update active tab - prevent text selection flicker
  document
    .querySelectorAll(".config-tab")
    .forEach((t) => t.classList.remove("active"));

  if (clickedElement && clickedElement.classList) {
    clickedElement.classList.add("active");
  } else {
    const tabElement = document.querySelector(
      `.config-tab:nth-child(${getTabIndex(tab)})`
    );
    if (tabElement) tabElement.classList.add("active");
  }

  if (!currentConfig) {
    document.getElementById("configTabContent").innerHTML =
      '<p class="placeholder">Loading configuration...</p>';
    return;
  }

  let html = "";

  switch (tab) {
    case "prices":
      html = `
                <div class="config-info-box">
                    <strong>💡 Price Thresholds:</strong> Define when prices are considered "low" or "high" for battery charging/discharging decisions.
                </div>
                <div class="config-form-grid">
                    <div class="config-form-group">
                        <label>Low Price Threshold</label>
                        <div class="config-description">Price below which to charge batteries from grid</div>
                        <div class="input-with-unit">
                            <input type="number" id="price_low_threshold" value="${currentConfig.price_thresholds.price_low_threshold}" step="0.01" min="0">
                            <span class="input-unit">lei/kWh</span>
                        </div>
                    </div>
                    <div class="config-form-group">
                        <label>High Price Threshold</label>
                        <div class="config-description">Price above which to discharge batteries to grid</div>
                        <div class="input-with-unit">
                            <input type="number" id="price_high_threshold" value="${currentConfig.price_thresholds.price_high_threshold}" step="0.01" min="0">
                            <span class="input-unit">lei/kWh</span>
                        </div>
                    </div>
                </div>
            `;
      break;

    case "grid":
      html = `
                <div class="config-info-box">
                    <strong>💡 Grid Limits:</strong> Maximum power that can flow to/from the grid and within the neighborhood.
                </div>
                <div class="config-form-grid">
                    <div class="config-form-group">
                        <label>Max Grid Import Power</label>
                        <div class="config-description">Maximum power that can be imported from grid</div>
                        <div class="input-with-unit">
                            <input type="number" id="p_grid_import_max_kw" value="${currentConfig.vpp_grid_limits.p_grid_import_max_kw}" step="100" min="0">
                            <span class="input-unit">kW</span>
                        </div>
                    </div>
                    <div class="config-form-group">
                        <label>Max Grid Export Power</label>
                        <div class="config-description">Maximum power that can be exported to grid</div>
                        <div class="input-with-unit">
                            <input type="number" id="p_grid_export_max_kw" value="${currentConfig.vpp_grid_limits.p_grid_export_max_kw}" step="100" min="0">
                            <span class="input-unit">kW</span>
                        </div>
                    </div>
                    <div class="config-form-group">
                        <label>Internal Line Limit</label>
                        <div class="config-description">Maximum power for internal trading between houses</div>
                        <div class="input-with-unit">
                            <input type="number" id="p_internal_line_limit_kw" value="${currentConfig.vpp_grid_limits.p_internal_line_limit_kw}" step="100" min="0">
                            <span class="input-unit">kW</span>
                        </div>
                    </div>
                </div>
            `;
      break;

    case "battery":
      html = `
                <div class="config-info-box">
                    <strong>💡 Battery Defaults:</strong> Default values for new batteries. Existing batteries won't be affected.
                </div>
                <div class="config-form-grid">
                    <div class="config-form-group">
                        <label>Battery Capacity</label>
                        <div class="config-description">Total energy storage capacity</div>
                        <div class="input-with-unit">
                            <input type="number" id="battery_capacity_kwh" value="${currentConfig.battery_defaults.battery_capacity_kwh}" step="1" min="0">
                            <span class="input-unit">kWh</span>
                        </div>
                    </div>
                    <div class="config-form-group">
                        <label>Min SOC Ratio</label>
                        <div class="config-description">Minimum state of charge to maintain (0-1)</div>
                        <div class="input-with-unit">
                            <input type="number" id="battery_soc_min_ratio" value="${currentConfig.battery_defaults.battery_soc_min_ratio}" step="0.05" min="0" max="1">
                            <span class="input-unit">ratio</span>
                        </div>
                    </div>
                    <div class="config-form-group">
                        <label>Max Charge Power</label>
                        <div class="config-description">Maximum charging power</div>
                        <div class="input-with-unit">
                            <input type="number" id="battery_p_ch_max_kw" value="${currentConfig.battery_defaults.battery_p_ch_max_kw}" step="0.5" min="0">
                            <span class="input-unit">kW</span>
                        </div>
                    </div>
                    <div class="config-form-group">
                        <label>Max Discharge Power</label>
                        <div class="config-description">Maximum discharging power</div>
                        <div class="input-with-unit">
                            <input type="number" id="battery_p_dis_max_kw" value="${currentConfig.battery_defaults.battery_p_dis_max_kw}" step="0.5" min="0">
                            <span class="input-unit">kW</span>
                        </div>
                    </div>
                </div>
            `;
      break;

    case "pv":
      html = `
                <div class="config-info-box">
                    <strong>💡 PV Defaults:</strong> Default PV capacity for new houses. Existing systems won't be affected.
                </div>
                <div class="config-form-grid">
                    <div class="config-form-group">
                        <label>PV Capacity</label>
                        <div class="config-description">Default solar panel capacity per house</div>
                        <div class="input-with-unit">
                            <input type="number" id="pv_capacity_kw" value="${currentConfig.pv_defaults.pv_capacity_kw}" step="0.5" min="0">
                            <span class="input-unit">kW</span>
                        </div>
                    </div>
                </div>
            `;
      break;

    case "trading":
      html = `
                <div class="config-info-box">
                    <strong>💡 Internal Trading:</strong> Configure pricing for energy traded between houses within the neighborhood.
                </div>
                <div class="config-form-grid">
                    <div class="config-form-group">
                        <label>Internal Price Discount</label>
                        <div class="config-description">Discount ratio for internal trading (0-1, e.g., 0.8 = 20% discount)</div>
                        <div class="input-with-unit">
                            <input type="number" id="internal_price_discount" value="${currentConfig.trading.internal_price_discount}" step="0.05" min="0" max="1">
                            <span class="input-unit">ratio</span>
                        </div>
                    </div>
                </div>
            `;
      break;
  }

  document.getElementById("configTabContent").innerHTML = html;
}

function getTabIndex(tab) {
  const tabs = ["prices", "grid", "battery", "pv", "trading"];
  return tabs.indexOf(tab) + 1;
}

async function saveConfig() {
  showLoading("Saving configuration...");

  try {
    // Collect all values from all tabs
    const updates = {};

    // Price thresholds
    const priceLow = document.getElementById("price_low_threshold");
    const priceHigh = document.getElementById("price_high_threshold");
    if (priceLow) updates.price_low_threshold = parseFloat(priceLow.value);
    if (priceHigh) updates.price_high_threshold = parseFloat(priceHigh.value);

    // Grid limits
    const gridImport = document.getElementById("p_grid_import_max_kw");
    const gridExport = document.getElementById("p_grid_export_max_kw");
    const internalLine = document.getElementById("p_internal_line_limit_kw");
    if (gridImport) updates.p_grid_import_max_kw = parseFloat(gridImport.value);
    if (gridExport) updates.p_grid_export_max_kw = parseFloat(gridExport.value);
    if (internalLine)
      updates.p_internal_line_limit_kw = parseFloat(internalLine.value);

    // Battery
    const battCap = document.getElementById("battery_capacity_kwh");
    const battSoc = document.getElementById("battery_soc_min_ratio");
    const battCharge = document.getElementById("battery_p_ch_max_kw");
    const battDischarge = document.getElementById("battery_p_dis_max_kw");
    if (battCap) updates.battery_capacity_kwh = parseFloat(battCap.value);
    if (battSoc) updates.battery_soc_min_ratio = parseFloat(battSoc.value);
    if (battCharge) updates.battery_p_ch_max_kw = parseFloat(battCharge.value);
    if (battDischarge)
      updates.battery_p_dis_max_kw = parseFloat(battDischarge.value);

    // PV
    const pvCap = document.getElementById("pv_capacity_kw");
    if (pvCap) updates.pv_capacity_kw = parseFloat(pvCap.value);

    // Trading
    const tradeDiscount = document.getElementById("internal_price_discount");
    if (tradeDiscount)
      updates.internal_price_discount = parseFloat(tradeDiscount.value);

    const response = await fetch(`${API_BASE_URL}/api/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });

    const data = await response.json();

    if (response.ok) {
      showToast("Configuration saved successfully! ✅", "success");
      currentConfig = data.current_config;
      showConfigTab(currentConfigTab);
    } else {
      showToast(`Failed to save: ${data.detail}`, "error");
    }
  } catch (error) {
    showToast("Error saving configuration: " + error.message, "error");
  } finally {
    hideLoading();
  }
}

async function resetConfig() {
  if (
    !confirm(
      "Are you sure you want to reset all configuration to default values?"
    )
  )
    return;

  showLoading("Resetting configuration...");

  try {
    const response = await fetch(`${API_BASE_URL}/api/config/reset`, {
      method: "POST",
    });

    const data = await response.json();

    if (response.ok) {
      showToast("Configuration reset to defaults! 🔄", "success");
      currentConfig = data.current_config;
      showConfigTab(currentConfigTab);
    } else {
      showToast("Failed to reset configuration", "error");
    }
  } catch (error) {
    showToast("Error: " + error.message, "error");
  } finally {
    hideLoading();
  }
}

// Live update functions for WebSocket data
function updateHouseDetailsLive(houseData) {
  const houseDetails = document.getElementById("houseDetails");
  if (!houseDetails) return;

  // Calculate energy balance values
  const pvProd = houseData.pv_prod_kw || 0;
  const totalLoad =
    houseData.L_total_kw || houseData.L_crit_kw + houseData.L_noncrit_kw;
  const balance = pvProd - totalLoad;
  const hasSurplus = pvProd >= totalLoad;

  // Update all house-info-item elements by finding their labels
  const infoItems = houseDetails.querySelectorAll(".house-info-item");
  infoItems.forEach((item) => {
    const label = item.querySelector(".house-info-label");
    const value = item.querySelector(".house-info-value");
    if (!label || !value) return;

    const labelText = label.textContent;

    // Battery updates
    if (labelText === "Current SOC" && houseData.battery) {
      value.textContent = houseData.battery.soc_kwh.toFixed(2) + " kWh";
    }
    if (labelText === "SOC Percentage" && houseData.battery) {
      value.textContent = houseData.battery.soc_percent.toFixed(1) + "%";
      item.style.borderColor =
        houseData.battery.soc_percent > 80
          ? "#10b981"
          : houseData.battery.soc_percent > 30
          ? "#f59e0b"
          : "#ef4444";
    }

    // Load updates
    if (labelText === "Critical Load") {
      value.textContent = houseData.L_crit_kw.toFixed(3) + " kW";
    }
    if (labelText === "Non-Critical Load") {
      value.textContent = houseData.L_noncrit_kw.toFixed(3) + " kW";
    }

    // Energy Balance updates
    if (labelText === "PV Production") {
      value.textContent = pvProd.toFixed(3) + " kW";
    }
    if (labelText === "Total Load") {
      value.textContent = totalLoad.toFixed(3) + " kW";
    }
    if (labelText === "Balance") {
      value.textContent = balance.toFixed(3) + " kW";
      item.style.borderColor = hasSurplus ? "#10b981" : "#ef4444";
    }
    if (labelText === "Status") {
      value.textContent = hasSurplus ? "☀️ Surplus" : "⚡ Deficit";
      value.style.color = hasSurplus ? "#10b981" : "#ef4444";
    }
  });

  // Update device statuses
  if (houseData.devices) {
    houseData.devices.forEach((device) => {
      const deviceItems = houseDetails.querySelectorAll(".device-item");
      deviceItems.forEach((item) => {
        const nameEl = item.querySelector(".device-name");
        if (nameEl && nameEl.textContent === device.name) {
          const statusEl = item.querySelector(".device-status");
          if (statusEl) {
            statusEl.className = `device-status ${
              device.status_on ? "on" : "off"
            }`;
            statusEl.textContent = device.status_on ? "ON" : "OFF";
          }
          const toggleEl = item.querySelector(".toggle-switch");
          if (toggleEl) {
            toggleEl.className = `toggle-switch ${
              device.status_on ? "active" : ""
            }`;
          }
        }
      });
    });
  }
}

function updateVPPStatsLive(data) {
  // Update live stats grid
  const updateEl = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  if (data.P_total_pv_kw !== undefined) {
    updateEl("livePvProd", data.P_total_pv_kw.toFixed(2));
  }
  if (data.P_total_load_kw !== undefined) {
    updateEl("liveTotalLoad", data.P_total_load_kw.toFixed(2));
  }
  if (data.P_grid_import_kw !== undefined) {
    updateEl("liveGridImport", data.P_grid_import_kw.toFixed(2));
  }
  if (data.P_grid_export_kw !== undefined) {
    updateEl("liveGridExport", data.P_grid_export_kw.toFixed(2));
  }
  if (data.P_internal_traded_kw !== undefined) {
    updateEl("liveInternalTrade", data.P_internal_traded_kw.toFixed(2));
  }
  if (data.avg_battery_soc_percent !== undefined) {
    updateEl("liveAvgSoc", data.avg_battery_soc_percent.toFixed(1));
  }

  // Update neighborhood state
  if (data.neighborhood_state) {
    const stateEl = document.getElementById("neighborhoodStateValue");
    if (stateEl) {
      stateEl.textContent = data.neighborhood_state;
      stateEl.style.color =
        data.neighborhood_state === "consum ridicat" ? "#ef4444" : "#10b981";
    }
  }

  // Update current price
  if (data.price_per_kwh !== undefined) {
    updateEl("currentPrice", data.price_per_kwh.toFixed(4));
  }
}

// Simulation Speed Control
async function setSimSpeed(seconds) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/sim/speed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interval_seconds: seconds }),
    });

    if (response.ok) {
      // Update UI
      document
        .querySelectorAll(".speed-btn")
        .forEach((btn) => btn.classList.remove("active"));
      document.getElementById(`speed${seconds}`)?.classList.add("active");
      document.getElementById("currentSpeed").textContent = seconds;
      showToast(`Speed set to ${seconds}s`, "success");
    }
  } catch (error) {
    showToast("Failed to set speed", "error");
  }
}

async function pauseSimulation() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/sim/pause`, {
      method: "POST",
    });

    if (response.ok) {
      document.getElementById("pauseBtn").style.display = "none";
      document.getElementById("resumeBtn").style.display = "inline-block";
      showToast("Simulation paused", "info");
    }
  } catch (error) {
    showToast("Failed to pause", "error");
  }
}

async function resumeSimulation() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/sim/resume`, {
      method: "POST",
    });

    if (response.ok) {
      document.getElementById("pauseBtn").style.display = "inline-block";
      document.getElementById("resumeBtn").style.display = "none";
      showToast("Simulation resumed", "success");
    }
  } catch (error) {
    showToast("Failed to resume", "error");
  }
}
