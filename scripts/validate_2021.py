#!/usr/bin/env python3
"""
scripts/validate_2021.py
Generates a publication-quality chart showing model backtesting on the 2021 drought.
Uses matplotlib: dark theme, multi-panel subplots, coloured bars per stress level.
Output: backend/validation_2021.png
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')            # Non-interactive backend (no display required)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import joblib
import warnings

warnings.filterwarnings('ignore')

# ── Config ──────────────────────────────────────────────────────────
STRESS_PATH = 'data/processed/stress_index.csv'
MODEL_PATH  = 'backend/model.pkl'
OUTPUT_PATH = 'backend/validation_2021.png'

COLORS    = ['#2ecc71', '#f39c12', '#e67e22', '#e74c3c']  # Normal→Emergency
LABELS    = ['Normal', 'Watch', 'Warning', 'Emergency']
DARK_BG   = '#0a0e1a'
PANEL_BG  = '#111827'
BORDER_COL = '#1f2937'

# ── Load Data & Model ──────────────────────────────────────────────
print("Loading model and stress data...")
model = joblib.load(MODEL_PATH)
df    = pd.read_csv(STRESS_PATH).dropna()

df = df.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)
# Add features (must match train_model.py exactly)
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

df['rain_z_lag1']    = df.groupby('oblast')['rain_zscore'].shift(1)
df['rain_z_lag2']    = df.groupby('oblast')['rain_zscore'].shift(2)
df['rain_z_lag3']    = df.groupby('oblast')['rain_zscore'].shift(3)
df['rain_z_lag4']    = df.groupby('oblast')['rain_zscore'].shift(4)

df['rain_z_roll3']   = df.groupby('oblast')['rain_z_lag1'].transform(
    lambda x: x.rolling(3, min_periods=2).mean()
)
df['rain_z_roll6']   = df.groupby('oblast')['rain_z_lag1'].transform(
    lambda x: x.rolling(6, min_periods=3).mean()
)

df['rain_z_trend']    = df['rain_z_lag1'] - df['rain_z_lag2']
df['roll3_lag1']    = df.groupby('oblast')['rolling_3mo_anomaly'].shift(1)

FEATURES = [
    'month_sin', 'month_cos',
    'rain_z_lag1', 'rain_z_lag2', 'rain_z_lag3', 'rain_z_lag4',
    'rain_z_roll3', 'rain_z_roll6',
    'rain_z_trend', 'roll3_lag1',
]

df_model = df.dropna(subset=FEATURES).copy()
df_model['predicted_level'] = model.predict(df_model[FEATURES])

# ── Select Target Oblasts ──────────────────────────────────────────
# Focus on southern oblasts most affected by the 2021 drought
# Using GAUL/NASA POWER oblast names (the real data uses these)
target_keywords = ['Yujno', 'Kyzylorda', 'Jambyl', 'Almatin', 'Mangistau']
target_oblasts  = []
for oblast in df_model['oblast'].unique():
    if any(kw.lower() in oblast.lower() for kw in target_keywords):
        target_oblasts.append(oblast)

if not target_oblasts:
    # Fallback: pick 4 oblasts with highest mean drought stress
    mean_stress    = df_model.groupby('oblast')['predicted_level'].mean()
    target_oblasts = mean_stress.sort_values(ascending=False).head(4).index.tolist()

print(f"  Plotting oblasts: {target_oblasts}")

# ── Filter 2020–2022 ───────────────────────────────────────────────
period = df_model[
    (df_model['year'].isin([2020, 2021, 2022])) &
    (df_model['oblast'].isin(target_oblasts))
].dropna(subset=FEATURES)

n_plots = max(len(target_oblasts), 1)

# ── Plot ─────────────────────────────────────────────────────────────
fig, axes = plt.subplots(
    n_plots, 1,
    figsize=(14, 3.5 * n_plots),
    facecolor=DARK_BG,
    constrained_layout=True
)
if n_plots == 1:
    axes = [axes]

for ax, oblast in zip(axes, target_oblasts):
    odf = period[period['oblast'] == oblast].sort_values(['year', 'month'])

    x          = range(len(odf))
    bar_colors = [COLORS[int(v)] for v in odf['predicted_level']]

    ax.bar(x, odf['predicted_level'], color=bar_colors, alpha=0.9, width=0.85)

    # Mark actual stress level with dots
    ax.scatter(x, odf['stress_level'], color='white', s=20, zorder=5,
               label='Actual label', alpha=0.7)

    # X-axis labels (every 3 months)
    tick_x      = list(range(0, len(odf), 3))
    tick_labels = [f"{r['year']}-{r['month']:02d}"
                   for _, r in odf.iloc[::3].iterrows()]
    ax.set_xticks(tick_x)
    ax.set_xticklabels(tick_labels, rotation=40, ha='right',
                       color='#9ca3af', fontsize=8)

    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(LABELS, color='white', fontsize=9)
    ax.set_ylim(-0.3, 3.6)
    ax.set_facecolor(PANEL_BG)
    ax.set_title(f'{oblast}  —  Predicted Drought Stress (2020–2022)',
                 color='white', fontsize=11, pad=8, loc='left')

    # Add vertical line at Jan 2021
    jan2021 = odf[(odf['year'] == 2021) & (odf['month'] == 1)]
    if not jan2021.empty:
        pos = odf.index.get_loc(jan2021.index[0])
        ax.axvline(pos, color='#60a5fa', linewidth=1.2, linestyle='--', alpha=0.7)
        ax.text(pos + 0.3, 3.3, '2021 Drought', color='#60a5fa', fontsize=8)

    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER_COL)
    ax.grid(axis='y', color=BORDER_COL, linewidth=0.5, alpha=0.5)

# Legend
legend_patches = [mpatches.Patch(color=COLORS[i], label=LABELS[i]) for i in range(4)]
legend_patches.append(mpatches.Patch(color='white', label='● Actual stress label'))
fig.legend(handles=legend_patches, loc='lower center',
           facecolor='#1f2937', edgecolor=BORDER_COL,
           labelcolor='white', fontsize=9,
           ncol=5, framealpha=0.9,
           bbox_to_anchor=(0.5, -0.04))

fig.suptitle(
    'AquaSentry — 2021 Central Asian Drought: Model Backtesting Validation',
    color='white', fontsize=13, y=1.01, fontweight='bold'
)

plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight', facecolor=DARK_BG)
print(f"\n✅ TASK A3.3 COMPLETE — Chart saved to {OUTPUT_PATH}")
print(f"   ← SEND THIS FILE TO MEMBER C FOR SLIDE 3 →")
plt.close(fig)
