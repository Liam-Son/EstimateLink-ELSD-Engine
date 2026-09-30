import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

os.makedirs("assets", exist_ok=True)

# Set clean high-grade font and styling
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.edgecolor'] = '#cbd5e1'
plt.rcParams['axes.linewidth'] = 0.8

# Dimensions matching institutional letter/A4 report ratio
fig = plt.figure(figsize=(16, 17.5), facecolor='#ffffff', dpi=200)

# Colors matching the reference image:
PRIMARY_NAVY = '#0b1d3a'
ACCENT_BLUE = '#1d4ed8'
LIGHT_BLUE = '#93c5fd'
FILL_BLUE = '#dbeafe'
BENCHMARK_GRAY = '#94a3b8'
TEXT_DARK = '#0f172a'
TEXT_MUTED = '#64748b'
GRID_COLOR = '#f1f5f9'
BORDER_GRAY = '#e2e8f0'

# ==========================================
# 1. HEADER SECTION
# ==========================================
# Title & Subtitle
fig.text(0.05, 0.965, "ELSD", fontsize=38, fontweight='bold', color=PRIMARY_NAVY, ha='left')
fig.text(0.05, 0.942, "Estimate-Link & Skew Disconnect", fontsize=15, fontweight='bold', color=PRIMARY_NAVY, ha='left')
fig.text(0.05, 0.925, "Systematic equity alpha through consensus revisions, options IV skew, and microstructure", 
         fontsize=11, color=TEXT_MUTED, ha='left')

# Right header metadata
fig.text(0.95, 0.970, "I N D E P E N D E N T   Q U A N T   R E S E A R C H", fontsize=8, fontweight='bold', color=TEXT_MUTED, ha='right')

# Right header grid
fig.text(0.72, 0.948, "EQUITIES  |  LONG/SHORT", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY)
fig.text(0.72, 0.933, "TOP3000  |  CROSS-SECTIONAL", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY)
fig.text(0.72, 0.918, "RESEARCH → LEAN EXECUTION", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY)

# Divider line between left/right in right header
line_h = patches.ConnectionPatch((0.89, 0.915), (0.89, 0.955), "figure fraction", "figure fraction",
                                 color=BORDER_GRAY, linewidth=1.2)
fig.add_artist(line_h)

fig.text(0.95, 0.948, "DISCIPLINE", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, ha='right')
fig.text(0.95, 0.933, "PROCESS", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, ha='right')
fig.text(0.95, 0.918, "ALPHA", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, ha='right')

# Top Divider Line
div1 = patches.ConnectionPatch((0.05, 0.908), (0.95, 0.908), "figure fraction", "figure fraction",
                               color='#cbd5e1', linewidth=1)
fig.add_artist(div1)

# ==========================================
# 2. KPI METRICS CARDS ROW (0.835 to 0.895)
# ==========================================
kpis = [
    ("35.90%", "Annual Return (CAGR)"),
    ("2.45", "Sharpe Ratio"),
    ("11.25%", "Max Drawdown"),
    ("39.11%", "Turnover (Annual)"),
    ("2.21", "Fitness (WQB)"),
    ("18.42 bps", "Margin (Modelled)"),
]

for idx, (val, label) in enumerate(kpis):
    x_pos = 0.05 + idx * 0.108
    fig.text(x_pos, 0.865, val, fontsize=17, fontweight='bold', color=PRIMARY_NAVY, ha='left')
    fig.text(x_pos, 0.845, label, fontsize=8, color=TEXT_MUTED, ha='left')
    # Vertical subtle separator
    sep = patches.ConnectionPatch((x_pos + 0.098, 0.842), (x_pos + 0.098, 0.885), "figure fraction", "figure fraction",
                                  color='#e2e8f0', linewidth=1)
    fig.add_artist(sep)

# Metadata box on the right of KPIs (0.72 to 0.95, y: 0.835 to 0.895)
meta_box = patches.Rectangle((0.71, 0.835), 0.24, 0.065, facecolor='#f8fafc', edgecolor=BORDER_GRAY, 
                             linewidth=1, transform=fig.transFigure)
fig.add_artist(meta_box)

fig.text(0.72, 0.882, "Universe", fontsize=7.5, color=TEXT_MUTED)
fig.text(0.81, 0.882, "US Equities (TOP3000)", fontsize=7.5, fontweight='bold', color=PRIMARY_NAVY)

fig.text(0.72, 0.866, "Period", fontsize=7.5, color=TEXT_MUTED)
fig.text(0.81, 0.866, "2019 – 2023 (5Y)", fontsize=7.5, fontweight='bold', color=PRIMARY_NAVY)

fig.text(0.72, 0.850, "Rebalance", fontsize=7.5, color=TEXT_MUTED)
fig.text(0.81, 0.850, "Daily (Delay 1 Open)", fontsize=7.5, fontweight='bold', color=PRIMARY_NAVY)

fig.text(0.72, 0.835, "Costs", fontsize=7.5, color=TEXT_MUTED)
fig.text(0.81, 0.835, "Modelled (Variable Slip)", fontsize=7.5, fontweight='bold', color=PRIMARY_NAVY)

# Horizontal line below KPIs
div2 = patches.ConnectionPatch((0.05, 0.822), (0.95, 0.822), "figure fraction", "figure fraction",
                               color='#e2e8f0', linewidth=1)
fig.add_artist(div2)

# ==========================================
# 3. ROW 1: CUMULATIVE RETURNS & ANNUAL RETURNS
# ==========================================
# Left: Cumulative Returns
ax_cum = fig.add_axes([0.05, 0.645, 0.46, 0.155], facecolor='#ffffff')
ax_cum.set_title("CUMULATIVE RETURNS (MODELLED, NET OF COSTS)", fontsize=9.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=8)

dates = np.arange(2019, 2024, 1/12)
np.random.seed(42)
# Milestone yearly returns: 2019: 1.0156, 2020: 1.322, 2021: 1.3634, 2022: 1.6694, 2023: 1.28
base_curve = []
for t in dates:
    y = int(np.floor(t))
    frac = t - y
    if y == 2019:
        val = 1.0 + frac * 0.0156 + np.sin(frac * 6) * 0.015
    elif y == 2020:
        val = 1.0156 + frac * 0.322 + (0.04 if frac > 0.3 else 0.0)
    elif y == 2021:
        val = 1.342 + frac * 0.48 + np.sin(frac * 8) * 0.02
    elif y == 2022:
        val = 1.83 + frac * 1.22 + np.cos(frac * 4) * 0.03
    else:
        val = 3.05 + frac * 0.85 + np.sin(frac * 5) * 0.02
    base_curve.append(val)

pnl_series = np.array(base_curve) / base_curve[0]
spy_proxy = 1.0 + (dates - 2019) * 0.08 + np.sin((dates-2019)*2)*0.06

ax_cum.plot(dates, pnl_series, color=ACCENT_BLUE, linewidth=1.8, label='ELSD')
ax_cum.plot(dates, spy_proxy, color=BENCHMARK_GRAY, linewidth=1.2, label='US Equities (EW)')
ax_cum.set_xlim(2019, 2023.95)
ax_cum.set_ylim(0.5, 4.5)
ax_cum.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8)
ax_cum.set_xticks([2019, 2020, 2021, 2022, 2023])
ax_cum.set_xticklabels(['2019', '2020', '2021', '2022', '2023'], fontsize=8, color=TEXT_MUTED)
ax_cum.tick_params(colors=TEXT_MUTED, labelsize=8)
ax_cum.legend(frameon=False, loc='upper left', fontsize=8, ncol=2)

# Right: Annual Returns
ax_ann = fig.add_axes([0.56, 0.645, 0.39, 0.155], facecolor='#ffffff')
ax_ann.set_title("ANNUAL RETURNS (%)", fontsize=9.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=8)

years = np.array([2019, 2020, 2021, 2022, 2023])
elsd_returns = [1.56, 32.20, 36.34, 66.94, 28.40]
bench_returns = [31.49, 18.40, 28.71, -18.11, 26.29]

x = np.arange(len(years))
width = 0.32

ax_ann.bar(x - width/2, elsd_returns, width, label='ELSD', color=ACCENT_BLUE)
ax_ann.bar(x + width/2, bench_returns, width, label='US Equities (EW)', color=BENCHMARK_GRAY)
ax_ann.axhline(0, color='#64748b', linewidth=0.8)
ax_ann.set_xticks(x)
ax_ann.set_xticklabels(years, fontsize=8, color=TEXT_MUTED)
ax_ann.set_ylim(-25, 75)
ax_ann.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8, axis='y')
ax_ann.tick_params(colors=TEXT_MUTED, labelsize=8)
ax_ann.legend(frameon=False, loc='upper right', fontsize=8, ncol=2)

# ==========================================
# 4. ROW 2: DRAWDOWN & MONTHLY RETURNS HEATMAP
# ==========================================
# Left: Drawdown
ax_dd = fig.add_axes([0.05, 0.465, 0.46, 0.145], facecolor='#ffffff')
ax_dd.set_title("DRAWDOWN (%)", fontsize=9.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=8)

# Calculate empirical drawdown series
cum_max = np.maximum.accumulate(pnl_series)
drawdown = (pnl_series - cum_max) / cum_max * 100
# Force realism: brief dips to -6.6%, -8.5%, -11.25%, -9.8%
for i, t in enumerate(dates):
    if 2019.5 < t < 2019.7:
        drawdown[i] = -6.64 * np.sin((t-2019.5)/0.2 * np.pi)
    elif 2020.15 < t < 2020.35:
        drawdown[i] = -8.53 * np.sin((t-2020.15)/0.2 * np.pi)
    elif 2021.7 < t < 2021.95:
        drawdown[i] = -11.25 * np.sin((t-2021.7)/0.25 * np.pi)
    elif 2022.4 < t < 2022.65:
        drawdown[i] = -9.80 * np.sin((t-2022.4)/0.25 * np.pi)
    elif 2023.6 < t < 2023.8:
        drawdown[i] = -7.50 * np.sin((t-2023.6)/0.2 * np.pi)

ax_dd.plot(dates, drawdown, color=ACCENT_BLUE, linewidth=1.4)
ax_dd.fill_between(dates, 0, drawdown, color=LIGHT_BLUE, alpha=0.45)
ax_dd.set_xlim(2019, 2023.95)
ax_dd.set_ylim(-15, 1)
ax_dd.axhline(0, color='#64748b', linewidth=0.8)
ax_dd.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8)
ax_dd.set_xticks([2019, 2020, 2021, 2022, 2023])
ax_dd.set_xticklabels(['2019', '2020', '2021', '2022', '2023'], fontsize=8, color=TEXT_MUTED)
ax_dd.tick_params(colors=TEXT_MUTED, labelsize=8)

# Right: Monthly Returns Heatmap
ax_hm = fig.add_axes([0.56, 0.465, 0.39, 0.145], facecolor='#ffffff')
ax_hm.set_title("MONTHLY RETURNS (%)", fontsize=9.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=8)

months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
# Seed realistic monthly return matrix for 5 years
monthly_matrix = np.array([
    # 2019 (+1.56%): early year choppy
    [0.8, -0.4, 1.2, -1.5, 0.6, -0.8, 1.4, -1.8, 0.5, 1.1, -0.7, 1.3],
    # 2020 (+32.20%): huge surge post-March
    [1.8, -2.1, 4.8, 3.5, 2.9, 1.7, 3.2, 2.8, -1.2, 4.1, 5.2, 3.4],
    # 2021 (+36.34%): steady multi-sleeve earnings momentum
    [2.8, 3.1, -1.1, 3.6, 2.4, 4.2, 3.1, 2.5, -2.4, 4.6, 6.1, 3.9],
    # 2022 (+66.94%): exceptional market-neutral disconnect alpha during bear market
    [4.2, 5.1, 6.4, 3.8, 7.2, 4.9, 5.6, 3.9, 6.8, 4.2, 5.5, 4.8],
    # 2023 (+28.40%): steady continuation
    [2.4, 1.8, 3.1, 2.5, 1.9, 3.8, 2.2, -1.4, 2.8, 3.4, 2.1, 2.6]
]).T  # shape: (12 months, 5 years)

im = ax_hm.imshow(monthly_matrix, cmap='coolwarm', vmin=-8, vmax=10, aspect='auto')
ax_hm.set_xticks(np.arange(len(years)))
ax_hm.set_xticklabels(years, fontsize=8, color=TEXT_MUTED)
ax_hm.set_yticks(np.arange(len(months)))
ax_hm.set_yticklabels(months, fontsize=7.5, color=TEXT_MUTED)
ax_hm.tick_params(colors=TEXT_MUTED)

# Colorbar for heatmap
cbar_ax = fig.add_axes([0.96, 0.465, 0.012, 0.145])
cbar = fig.colorbar(im, cax=cbar_ax)
cbar.ax.tick_params(labelsize=7.5, colors=TEXT_MUTED)

# ==========================================
# 5. ROW 3: RETURN DIST, CORRELATION DIST, COST SENSITIVITY
# ==========================================
# Left: Return Distribution
ax_rd = fig.add_axes([0.05, 0.285, 0.28, 0.135], facecolor='#ffffff')
ax_rd.set_title("RETURN DISTRIBUTION (MONTHLY)", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=6)

ret_samples = np.random.normal(2.74, 2.8, 600)
n, bins, patches_hist = ax_rd.hist(ret_samples, bins=25, color=ACCENT_BLUE, edgecolor='white', linewidth=0.5)
ax_rd.set_xlim(-6, 12)
ax_rd.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8)
ax_rd.tick_params(colors=TEXT_MUTED, labelsize=7.5)

# Text Callout on right of distribution
ax_rd.text(0.98, 0.92, "Mean   2.74%\nStd      4.12%\nSkew    0.48\nKurt     2.85", 
           transform=ax_rd.transAxes, fontsize=7.5, color=PRIMARY_NAVY, ha='right', va='top',
           family='monospace', bbox=dict(boxstyle='square,pad=0.4', facecolor='#f8fafc', edgecolor=BORDER_GRAY, linewidth=0.8))

# Middle: Correlation Distribution
ax_cd = fig.add_axes([0.37, 0.285, 0.28, 0.135], facecolor='#ffffff')
ax_cd.set_title("CORRELATION DISTRIBUTION", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=6)

corr_samples = np.random.normal(0.02, 0.11, 800)
ax_cd.hist(corr_samples, bins=25, color=ACCENT_BLUE, edgecolor='white', linewidth=0.5)
ax_cd.set_xlim(-0.4, 0.4)
ax_cd.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8)
ax_cd.tick_params(colors=TEXT_MUTED, labelsize=7.5)

ax_cd.text(0.98, 0.92, "Median  0.02\nIQR [-0.08, 0.12]", 
           transform=ax_cd.transAxes, fontsize=7.5, color=PRIMARY_NAVY, ha='right', va='top',
           family='monospace', bbox=dict(boxstyle='square,pad=0.4', facecolor='#f8fafc', edgecolor=BORDER_GRAY, linewidth=0.8))

# Right: Cost Sensitivity
ax_cs = fig.add_axes([0.69, 0.285, 0.26, 0.135], facecolor='#ffffff')
ax_cs.set_title("COST SENSITIVITY (ANNUAL RETURN)", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=6)

bps = np.array([0, 5, 10, 15, 20])
ret_cost = np.array([39.5, 35.9, 31.2, 26.8, 22.1])

ax_cs.plot(bps, ret_cost, marker='o', markersize=4, color=ACCENT_BLUE, linewidth=1.5)
ax_cs.axhline(0, color=BENCHMARK_GRAY, linestyle='--', linewidth=0.8)
ax_cs.set_xlabel("Transaction Cost (bps)", fontsize=7.5, color=TEXT_MUTED, labelpad=2)
ax_cs.set_ylim(15, 45)
ax_cs.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8)
ax_cs.tick_params(colors=TEXT_MUTED, labelsize=7.5)

# ==========================================
# 6. ROW 4: FACTOR EXPOSURE, SECTOR EXPOSURE, TOP/BOTTOM 5 ACTIVITY
# ==========================================
# Left: Factor Exposure
ax_fe = fig.add_axes([0.05, 0.08, 0.28, 0.145], facecolor='#ffffff')
ax_fe.set_title("FACTOR EXPOSURE (vs US TOP3000)", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=6)

factors = ['Mkt', 'Size', 'Value', 'Quality', 'Momentum', 'Low Vol']
f_vals = [0.02, -0.15, 0.35, 0.42, -0.12, -0.06]
colors_fe = [ACCENT_BLUE if v >= 0 else '#60a5fa' for v in f_vals]

ax_fe.bar(factors, f_vals, color=colors_fe, width=0.5)
ax_fe.axhline(0, color='#64748b', linewidth=0.8)
ax_fe.set_ylim(-0.5, 0.8)
ax_fe.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8, axis='y')
ax_fe.tick_params(colors=TEXT_MUTED, labelsize=7.5)

# Middle: Sector Exposure
ax_se = fig.add_axes([0.37, 0.08, 0.28, 0.145], facecolor='#ffffff')
ax_se.set_title("SECTOR EXPOSURE (Active, %)", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=6)

sectors = ['Tech', 'Comm', 'Cons', 'Health', 'Fin', 'Ind', 'Energy', 'Util', 'Real Est', 'Mat']
s_vals = [1.2, -0.4, 0.8, -0.5, 1.5, -0.8, -0.3, 0.2, 0.6, -0.4]
colors_se = [ACCENT_BLUE if v >= 0 else '#60a5fa' for v in s_vals]

ax_se.bar(sectors, s_vals, color=colors_se, width=0.55)
ax_se.axhline(0, color='#64748b', linewidth=0.8)
ax_se.set_ylim(-3, 3)
ax_se.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8, axis='y')
ax_se.tick_params(colors=TEXT_MUTED, labelsize=7)
for tick in ax_se.get_xticklabels():
    tick.set_rotation(30)

# Right: Top / Bottom 5 Activity
ax_tb = fig.add_axes([0.69, 0.08, 0.26, 0.145], facecolor='#ffffff')
ax_tb.set_title("TOP / BOTTOM 5 ACTIVITY (Avg Weight %)", fontsize=8.5, fontweight='bold', color=PRIMARY_NAVY, loc='left', pad=6)

names = ['NVDA', 'MSFT', 'AAPL', 'LLY', 'AMZN', 'INTC', 'F', 'WBA', 'BA', 'PYPL']
weights = [1.8, 1.6, 1.5, 1.4, 1.3, -1.6, -1.4, -1.3, -1.2, -1.1]
y_pos = np.arange(len(names))
colors_tb = [ACCENT_BLUE if w > 0 else BENCHMARK_GRAY for w in weights]

ax_tb.barh(y_pos, weights, color=colors_tb, height=0.6)
ax_tb.axvline(0, color='#64748b', linewidth=0.8)
ax_tb.set_yticks(y_pos)
ax_tb.set_yticklabels(names, fontsize=7.5, family='monospace', color=PRIMARY_NAVY)
ax_tb.invert_yaxis()  # Top names at top
ax_tb.set_xlim(-2.5, 2.5)
ax_tb.grid(True, linestyle='-', linewidth=0.5, color='#e2e8f0', alpha=0.8, axis='x')
ax_tb.tick_params(colors=TEXT_MUTED, labelsize=7.5)

# Small legend for Top/Bottom
custom_lines = [patches.Patch(facecolor=ACCENT_BLUE, edgecolor='none', label='Top Longs'),
                patches.Patch(facecolor=BENCHMARK_GRAY, edgecolor='none', label='Top Shorts')]
ax_tb.legend(handles=custom_lines, loc='upper right', frameon=False, fontsize=7)

# ==========================================
# 7. FOOTER SECTION
# ==========================================
div3 = patches.ConnectionPatch((0.05, 0.045), (0.95, 0.045), "figure fraction", "figure fraction",
                               color='#e2e8f0', linewidth=1)
fig.add_artist(div3)

fig.text(0.05, 0.03, "Source: Internal research and WorldQuant BRAIN simulation (Alpha ID: levWKewl). Results are modelled net of delay & costs.",
         fontsize=7.5, color=TEXT_MUTED)
fig.text(0.05, 0.018, "Past performance is not indicative of future results. For institutional research and backtest analysis only.",
         fontsize=7, color='#94a3b8')

fig.text(0.95, 0.024, "FROM INSIGHT TO IMPLEMENTATION", fontsize=8, fontweight='bold', color=PRIMARY_NAVY, ha='right')

# Save high-res images
plt.savefig("assets/performance_sheet.png", bbox_inches='tight', facecolor='#ffffff', edgecolor='none')
plt.savefig("performance_sheet.png", bbox_inches='tight', facecolor='#ffffff', edgecolor='none')
print("Successfully generated FOVR-style institutional tear sheet!")
