import os
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import r2_score, mean_absolute_error, accuracy_score, classification_report
import joblib

def train_models():
    input_file = "backend/data/processed/ml_training_data.json"
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Cleaned training data {input_file} not found. Please run spark_pipeline.py first.")
        
    print(f"Loading preprocessed dataset from {input_file}...")
    with open(input_file, "r") as f:
        data = json.load(f)
        
    df = pd.DataFrame(data)
    print(f"Loaded {len(df)} rows.")

    # 1. Feature Preprocessing
    print("Preprocessing features...")
    
    # Categorical features for OneHotEncoding
    categorical_cols = ["job_title", "experience_level", "job_type", "industry"]
    
    # Extract unique values of categories for frontend/API reference
    metadata = {}
    for col in categorical_cols:
        metadata[col] = sorted(df[col].unique().tolist())
        
    # Fit OneHotEncoder on categorical features
    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    X_cat = ohe.fit_transform(df[categorical_cols])
    cat_feature_names = ohe.get_feature_names_out(categorical_cols).tolist()
    
    # Fit MultiLabelBinarizer on skills
    mlb = MultiLabelBinarizer()
    X_skills = mlb.fit_transform(df["skills"])
    skills_list = mlb.classes_.tolist()
    metadata["skills"] = skills_list
    
    # Combine features into final training matrix
    X = np.hstack((X_cat, X_skills))
    
    # Target variables
    y_salary = df["salary"].values
    
    # Map demand score categories to numbers: Low -> 0, Medium -> 1, High -> 2
    demand_mapping = {"Low": 0, "Medium": 1, "High": 2}
    y_demand = df["demand_score"].map(demand_mapping).values
    
    # Save categories metadata to processed data folder
    with open("backend/data/processed/metadata_options.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print("Metadata options saved.")
        
    # 2. Train-Test Split
    print("Splitting datasets...")
    # Split for salary model
    X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(X, y_salary, test_size=0.2, random_state=42)
    # Split for demand model
    X_train_d, X_test_d, y_train_d, y_test_d = train_test_split(X, y_demand, test_size=0.2, random_state=42)
    
    # 3. Train Salary Regression Model (Random Forest Regressor)
    print("Training Random Forest Regressor for Salary Prediction...")
    # Use reasonable hyperparameters for fast training with 100k samples
    salary_model = RandomForestRegressor(n_estimators=50, max_depth=15, random_state=42, n_jobs=-1)
    salary_model.fit(X_train_s, y_train_s)
    
    # Evaluate salary model
    y_pred_s = salary_model.predict(X_test_s)
    r2 = r2_score(y_test_s, y_pred_s)
    mae = mean_absolute_error(y_test_s, y_pred_s)
    print(f"Salary Model Evaluation:")
    print(f"  R2 Score: {r2:.4f}")
    print(f"  Mean Absolute Error (MAE): ${mae:.2f}")
    
    # 4. Train Demand Classification Model (Random Forest Classifier)
    print("Training Random Forest Classifier for Demand Prediction...")
    demand_model = RandomForestClassifier(n_estimators=50, max_depth=15, random_state=42, n_jobs=-1)
    demand_model.fit(X_train_d, y_train_d)
    
    # Evaluate demand model
    y_pred_d = demand_model.predict(X_test_d)
    acc = accuracy_score(y_test_d, y_pred_d)
    print(f"Demand Model Evaluation:")
    print(f"  Accuracy Score: {acc:.4f}")
    print("Classification Report:")
    print(classification_report(y_test_d, y_pred_d, target_names=["Low", "Medium", "High"]))
    
    # Calculate feature importances to show top driver skills/features
    print("Computing feature importances...")
    importances = salary_model.feature_importances_
    all_feature_names = cat_feature_names + skills_list
    feature_importance_map = dict(zip(all_feature_names, importances.tolist()))
    
    with open("backend/data/processed/feature_importances.json", "w") as f:
        json.dump(feature_importance_map, f, indent=2)

    # 5. Save Models and Encoders
    os.makedirs("backend/models", exist_ok=True)
    
    joblib.dump(salary_model, "backend/models/salary_model.pkl")
    joblib.dump(demand_model, "backend/models/demand_model.pkl")
    joblib.dump(ohe, "backend/models/one_hot_encoder.pkl")
    joblib.dump(mlb, "backend/models/skills_binarizer.pkl")
    
    print("All models and encoders saved successfully in backend/models/")

if __name__ == "__main__":
    train_models()
