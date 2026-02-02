import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Load CSV
try:
    data = pd.read_csv("diabetes.csv")  # CSV should be in same folder
except FileNotFoundError:
    print("❌ diabetes.csv file same folder lo ledu")
    exit()

# Fill missing values
data = data.fillna(0)

# Features and target
X = data.drop("Outcome", axis=1)
y = data["Outcome"]

# Scale features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Logistic Regression model
model = LogisticRegression()
model.fit(X_train, y_train)

# Save model + scaler
with open("diabetes_model.pkl", "wb") as f:
    pickle.dump((model, scaler), f)

print("✅ diabetes_model.pkl created successfully")
