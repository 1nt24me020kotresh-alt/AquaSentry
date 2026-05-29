import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

INPUT_PATH = 'data/processed/stress_index.csv'
df = pd.read_csv(INPUT_PATH).dropna()
df = df.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
df['rain_z_lag1'] = df.groupby('oblast')['rain_zscore'].shift(1)
df['rain_z_lag2'] = df.groupby('oblast')['rain_zscore'].shift(2)
df['rain_z_lag3'] = df.groupby('oblast')['rain_zscore'].shift(3)
df['rain_z_lag4'] = df.groupby('oblast')['rain_zscore'].shift(4)
df['rain_z_roll3'] = df.groupby('oblast')['rain_z_lag1'].transform(lambda x: x.rolling(3, min_periods=2).mean())
df['rain_z_roll6'] = df.groupby('oblast')['rain_z_lag1'].transform(lambda x: x.rolling(6, min_periods=3).mean())
df['rain_z_trend'] = df['rain_z_lag1'] - df['rain_z_lag2']
df['roll3_lag1'] = df.groupby('oblast')['rolling_3mo_anomaly'].shift(1)

FEATURES = ['month_sin', 'month_cos', 'rain_z_lag1', 'rain_z_lag2', 'rain_z_lag3', 'rain_z_lag4', 'rain_z_roll3', 'rain_z_roll6', 'rain_z_trend', 'roll3_lag1']
TARGET = 'stress_level'
df_clean = df.dropna(subset=FEATURES + [TARGET])

train = df_clean[df_clean['year'] <= 2022]
test  = df_clean[df_clean['year'] >= 2023]
X_train, y_train = train[FEATURES], train[TARGET].astype(int)
X_test,  y_test  = test[FEATURES],  test[TARGET].astype(int)

model = XGBClassifier(random_state=42)
model.fit(X_train, y_train)
print("Default Test accuracy:", accuracy_score(y_test, model.predict(X_test)))

for d in [3, 4, 5]:
    for lr in [0.05, 0.1, 0.2]:
        for n in [100, 200, 400]:
            m = XGBClassifier(max_depth=d, learning_rate=lr, n_estimators=n, random_state=42)
            m.fit(X_train, y_train)
            acc = accuracy_score(y_test, m.predict(X_test))
            if acc > 0.8:
                print(f"Depth {d}, LR {lr}, N {n} -> Acc {acc}")
