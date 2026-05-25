import os
import json
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import joblib

app = FastAPI(title="Job Market Trend Analyzer API", version="1.0.0")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for models and preprocessors
MODELS_LOADED = False
salary_model = None
demand_model = None
ohe = None
mlb = None
metadata_options = {}
feature_importances = {}

# Paths
PROCESSED_DATA_DIR = "backend/data/processed"
MODELS_DIR = "backend/models"

def load_resources():
    global MODELS_LOADED, salary_model, demand_model, ohe, mlb, metadata_options, feature_importances
    try:
        if os.path.exists(f"{MODELS_DIR}/salary_model.pkl"):
            salary_model = joblib.load(f"{MODELS_DIR}/salary_model.pkl")
            demand_model = joblib.load(f"{MODELS_DIR}/demand_model.pkl")
            ohe = joblib.load(f"{MODELS_DIR}/one_hot_encoder.pkl")
            mlb = joblib.load(f"{MODELS_DIR}/skills_binarizer.pkl")
            
            with open(f"{PROCESSED_DATA_DIR}/metadata_options.json", "r") as f:
                metadata_options = json.load(f)
                
            if os.path.exists(f"{PROCESSED_DATA_DIR}/feature_importances.json"):
                with open(f"{PROCESSED_DATA_DIR}/feature_importances.json", "r") as f:
                    feature_importances = json.load(f)
                    
            MODELS_LOADED = True
            print("Successfully loaded ML models and encoders.")
        else:
            print("Models not trained yet. Run train_model.py first.")
    except Exception as e:
        print(f"Error loading models: {e}")

@app.on_event("startup")
def startup_event():
    load_resources()

# Pydantic models for request validation
class JobInput(BaseModel):
    job_title: str
    experience_level: str
    job_type: str
    industry: str
    skills: List[str]

# Health check
@app.get("/api/health")
def health():
    return {"status": "ok", "models_loaded": MODELS_LOADED}

# Metadata options for select inputs
@app.get("/api/metadata")
def get_metadata():
    if not MODELS_LOADED:
        load_resources()
    if not MODELS_LOADED:
        raise HTTPException(status_code=503, detail="Models and metadata not loaded. Train the models first.")
    return metadata_options

# Analytics metrics from PySpark output
@app.get("/api/insights")
def get_insights():
    try:
        stats = {}
        with open(f"{PROCESSED_DATA_DIR}/overall_stats.json", "r") as f:
            stats["overall"] = json.load(f)
        with open(f"{PROCESSED_DATA_DIR}/skills_analysis.json", "r") as f:
            stats["skills"] = json.load(f)[:15] # Top 15 skills
        with open(f"{PROCESSED_DATA_DIR}/salary_by_title_exp.json", "r") as f:
            stats["salary_trends"] = json.load(f)
        with open(f"{PROCESSED_DATA_DIR}/industry_metrics.json", "r") as f:
            stats["industry_metrics"] = json.load(f)
        with open(f"{PROCESSED_DATA_DIR}/salary_distribution.json", "r") as f:
            stats["salary_distribution"] = json.load(f)
        return stats
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404, 
            detail=f"Insights files not found. Ensure Spark pipeline is run first. Details: {str(e)}"
        )

# ML Prediction Endpoint
@app.post("/api/predict")
def predict_salary_and_demand(job: JobInput):
    if not MODELS_LOADED:
        load_resources()
    if not MODELS_LOADED:
        raise HTTPException(status_code=503, detail="Machine learning models are not initialized.")
        
    try:
        # Preprocess input categories using OneHotEncoder
        cat_data = pd.DataFrame([{
            "job_title": job.job_title,
            "experience_level": job.experience_level,
            "job_type": job.job_type,
            "industry": job.industry
        }])
        X_cat = ohe.transform(cat_data)
        
        # Preprocess skills using MultiLabelBinarizer
        X_skills = mlb.transform([job.skills])
        
        # Combine
        X = np.hstack((X_cat, X_skills))
        
        # Predict Salary
        predicted_salary = salary_model.predict(X)[0]
        
        # Predict Demand Score
        demand_class_idx = demand_model.predict(X)[0]
        demand_mapping_rev = {0: "Low", 1: "Medium", 2: "High"}
        predicted_demand = demand_mapping_rev[demand_class_idx]
        
        # Dynamic Skill Booster Analysis:
        # Find which skills are NOT in the input, add them one by one, and predict salary to see impact
        available_skills = metadata_options.get("skills", [])
        missing_skills = [s for s in available_skills if s not in job.skills]
        
        skill_boosts = []
        # Limit to checking top 15 most important skills to keep prediction speedy
        top_skills_to_check = [s for s in missing_skills if s in feature_importances][:15]
        
        for skill in top_skills_to_check:
            temp_skills = job.skills + [skill]
            X_temp_skills = mlb.transform([temp_skills])
            X_temp = np.hstack((X_cat, X_temp_skills))
            temp_salary = salary_model.predict(X_temp)[0]
            boost = temp_salary - predicted_salary
            if boost > 500: # Only report positive boosts
                skill_boosts.append({
                    "skill": skill,
                    "boost_amount": round(boost, 2)
                })
        
        # Sort recommendations by boost amount descending
        skill_boosts = sorted(skill_boosts, key=lambda x: x["boost_amount"], reverse=True)[:3]

        return {
            "predicted_salary": round(predicted_salary, 2),
            "demand_score": predicted_demand,
            "recommendations": skill_boosts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

# Career Roadmap Planner
@app.get("/api/skills-roadmap")
def get_skills_roadmap(current_skills: str):
    # Parse comma separated skills
    user_skills = [s.strip() for s in current_skills.split(",") if s.strip()]
    if not user_skills:
        return {"roadmap": []}
        
    try:
        # Load skills aggregation to find average paying and popular skills
        with open(f"{PROCESSED_DATA_DIR}/skills_analysis.json", "r") as f:
            skills_data = json.load(f)
            
        # Build skill information lookup
        skills_lookup = {item["skill"]: item for item in skills_data}
        
        # Recommendations: Find high-paying or popular skills NOT in user's list
        recommendations = []
        for item in skills_data:
            skill = item["skill"]
            if skill not in user_skills:
                recommendations.append({
                    "skill": skill,
                    "frequency": item["frequency"],
                    "avg_salary": item["avg_salary"],
                    "priority": "High" if item["avg_salary"] > 115000 else "Medium"
                })
                
        # Limit to top 5 recommendations
        top_recs = recommendations[:5]
        
        # Create a simple visual road map path
        roadmap = []
        for i, rec in enumerate(top_recs):
            roadmap.append({
                "step": i + 1,
                "skill": rec["skill"],
                "target_avg_salary": rec["avg_salary"],
                "reason": f"Expands market capability, median salary is ${rec['avg_salary']:,.2f}.",
                "priority": rec["priority"]
            })
            
        return {"roadmap": roadmap}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Roadmap error: {str(e)}")

# Job Listings Search
@app.get("/api/jobs")
def search_jobs(title: str = None, industry: str = None, type: str = None):
    try:
        with open("backend/data/jobs_large.json", "r") as f:
            jobs = json.load(f)
            
        # Filter a small subset (e.g. 50 jobs) to send to frontend for listing
        filtered = []
        for j in jobs:
            if title and title.lower() not in j["job_title"].lower():
                continue
            if industry and industry.lower() != j["industry"].lower():
                continue
            if type and type.lower() != j["job_type"].lower():
                continue
            filtered.append(j)
            if len(filtered) >= 40:
                break
        return filtered
    except FileNotFoundError:
        return []

# Career Roadmap Generator based on role
@app.post("/api/roadmap")
def generate_role_roadmap(role: str):
    role_frameworks = {
        "Data Scientist": [
            {"title": "Core Foundations", "description": "Master mathematical foundations, statistics, Python programming, and data querying.", "base_skills": ["Python", "SQL"]},
            {"title": "Big Data Engineering", "description": "Leverage Spark and Hadoop for distributed datasets and cleaning at scale.", "base_skills": ["PySpark", "Hadoop"]},
            {"title": "Machine Learning", "description": "Implement Random Forest, deep models, and serialize artifacts for serving.", "base_skills": ["Machine Learning", "Scikit-Learn"]}
        ],
        "Machine Learning Engineer": [
            {"title": "Algorithms & Data", "description": "Build high-performance feature pipelines and custom statistical models.", "base_skills": ["Python", "Machine Learning"]},
            {"title": "Big Data & Ingestion", "description": "Process stream and batch jobs using Apache Spark.", "base_skills": ["PySpark", "Kubernetes"]},
            {"title": "Model Deployment", "description": "Package inference APIs in FastAPI and containerize services.", "base_skills": ["Docker", "AWS", "FastAPI"]}
        ],
        "Data Analyst": [
            {"title": "Data Querying", "description": "Write advanced relational database queries and structure raw schemas.", "base_skills": ["SQL"]},
            {"title": "Analysis & Viz", "description": "Create dashboard reports and perform exploratory statistical sweeps.", "base_skills": ["Python", "PowerBI"]},
            {"title": "Version Control", "description": "Manage files and collaborative pipelines cleanly.", "base_skills": ["Git"]}
        ],
        "DevOps Engineer": [
            {"title": "Automation & Versioning", "description": "Master Git workflows, bash scripting, and deployment pipelines.", "base_skills": ["Git"]},
            {"title": "Containerization", "description": "Create clean dockerized microservices and manage resource limits.", "base_skills": ["Docker"]},
            {"title": "Orchestration & Cloud", "description": "Manage cloud clusters and automated scaling profiles.", "base_skills": ["Kubernetes", "AWS"]}
        ],
        "Cloud Architect": [
            {"title": "Cloud Networking", "description": "Configure virtual private clouds, load balancers, and security layers.", "base_skills": ["AWS"]},
            {"title": "Container Deployment", "description": "Containerize cluster jobs and schedule background services.", "base_skills": ["Docker", "Kubernetes"]},
            {"title": "Scalable Frameworks", "description": "Configure large data frameworks and real-time streams.", "base_skills": ["Hadoop", "PySpark"]}
        ],
        "Data Engineer": [
            {"title": "Database Systems", "description": "Master SQL query patterns and relational tables.", "base_skills": ["SQL"]},
            {"title": "Big Data Pipelines", "description": "Configure PySpark transformations and schema cleansing maps.", "base_skills": ["PySpark", "Hadoop"]},
            {"title": "Orchestration", "description": "Automate data workflows, container schedules, and API triggers.", "base_skills": ["Docker", "AWS"]}
        ],
        "Backend Developer": [
            {"title": "Language Mastery", "description": "Build clean backend routing structures and manage OOP patterns.", "base_skills": ["Python", "JavaScript"]},
            {"title": "API Frameworks", "description": "Expose REST endpoints and configure database ORMs.", "base_skills": ["FastAPI", "SQL"]},
            {"title": "Deploy & Containerize", "description": "Deploy services to production clouds using Docker.", "base_skills": ["Docker", "Git"]}
        ]
    }
    
    selected_framework = role_frameworks.get(role, role_frameworks["Data Scientist"])
    
    try:
        with open(f"{PROCESSED_DATA_DIR}/skills_analysis.json", "r") as f:
            skills_data = json.load(f)
        skills_lookup = {item["skill"]: item for item in skills_data}
    except Exception:
        skills_lookup = {}
        
    milestones = []
    for milestone in selected_framework:
        enriched_skills = []
        for s in milestone["base_skills"]:
            lookup = skills_lookup.get(s, {})
            enriched_skills.append(s)
        
        milestones.append({
            "title": milestone["title"],
            "description": milestone["description"],
            "skills": enriched_skills
        })
        
    return {
        "role": role,
        "milestones": milestones
    }

# Mount static files at the root
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="static")
