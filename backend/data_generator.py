import json
import random
import uuid
from datetime import datetime, timedelta

def generate_job_postings(num_records=100000):
    job_titles = {
        "Software Engineer": ["Java", "Python", "SQL", "Git", "Docker", "AWS", "Spring Boot", "REST APIs"],
        "Data Scientist": ["Python", "SQL", "Machine Learning", "PySpark", "TensorFlow", "Pandas", "Statistics", "R"],
        "Frontend Developer": ["JavaScript", "TypeScript", "React", "HTML/CSS", "Redux", "Sass", "Git", "Webpack"],
        "Backend Developer": ["Node.js", "Python", "Go", "PostgreSQL", "MongoDB", "Redis", "Docker", "REST APIs"],
        "Fullstack Developer": ["JavaScript", "React", "Node.js", "Express", "MongoDB", "TypeScript", "Git", "SQL"],
        "DevOps Engineer": ["Docker", "Kubernetes", "AWS", "CI/CD", "Terraform", "Linux", "Bash", "Python"],
        "Data Engineer": ["PySpark", "Hadoop", "SQL", "Python", "Scala", "ETL", "Airflow", "Kafka"],
        "Product Manager": ["Agile", "Scrum", "Product Roadmap", "Jira", "SQL", "Data Analytics", "UI/UX Concepts", "A/B Testing"],
        "Cyber Security Analyst": ["Firewalls", "SIEM", "Penetration Testing", "Linux", "Network Security", "Cryptography", "Wireshark", "Python"],
        "Cloud Architect": ["AWS", "Azure", "GCP", "Kubernetes", "Terraform", "Cloud Security", "Enterprise Architecture", "Docker"]
    }

    industries = ["Tech", "Finance", "Healthcare", "E-Commerce", "Education"]
    locations = ["New York, NY", "San Francisco, CA", "Seattle, WA", "Austin, TX", "Boston, MA", "Chicago, IL", "London, UK", "Karachi, PK", "Toronto, ON", "Berlin, DE"]
    experience_levels = ["Entry-level", "Mid-level", "Senior", "Lead"]
    job_types = ["Remote", "Hybrid", "Onsite"]
    companies = [
        "Google", "Meta", "Amazon", "Microsoft", "Netflix", "Apple", "Stripe", "Airbnb", "Uber", "Lyft",
        "JPMorgan Chase", "Goldman Sachs", "Citigroup", "Pfizer", "Moderna", "UnitedHealth", "Shopify", 
        "Etsy", "Coursera", "Udemy", "System Ltd", "Folio3", "Turing", "10Pearls"
    ]

    base_salaries = {
        "Software Engineer": 95000,
        "Data Scientist": 105000,
        "Frontend Developer": 85000,
        "Backend Developer": 90000,
        "Fullstack Developer": 95000,
        "DevOps Engineer": 105000,
        "Data Engineer": 100000,
        "Product Manager": 110000,
        "Cyber Security Analyst": 95000,
        "Cloud Architect": 125000
    }

    experience_multipliers = {
        "Entry-level": 0.7,
        "Mid-level": 1.0,
        "Senior": 1.4,
        "Lead": 1.7
    }

    jobs = []
    start_date = datetime.now() - timedelta(days=365)

    for i in range(num_records):
        title = random.choice(list(job_titles.keys()))
        industry = random.choice(industries)
        
        # Determine job type & location
        job_type = random.choice(job_types)
        location = "Remote" if job_type == "Remote" else random.choice(locations)
        
        experience = random.choice(experience_levels)
        company = random.choice(companies)
        
        # Select 3-6 skills for this job
        available_skills = job_titles[title]
        # Mix in a few general industry skills
        general_skills = ["Communication", "Problem Solving", "Agile", "SQL", "Git"]
        all_candidate_skills = list(set(available_skills + general_skills))
        skills_count = random.randint(3, 6)
        skills = random.sample(all_candidate_skills, skills_count)
        
        # Calculate salary
        base = base_salaries[title]
        mult = experience_multipliers[experience]
        salary = base * mult
        
        # Skill premiums
        premium = 0
        for skill in skills:
            if skill in ["PySpark", "Kubernetes", "TensorFlow", "Terraform", "Cloud Architect", "AWS", "Go"]:
                premium += 8000
            elif skill in ["Python", "React", "TypeScript", "Docker", "CI/CD"]:
                premium += 4000
        
        salary += premium
        
        # Job type adjustment
        if job_type == "Remote":
            salary += 5000
        elif job_type == "Onsite":
            salary -= 3000
            
        # Add random noise (normal distribution)
        salary += random.normalvariate(0, 6000)
        salary = max(30000, round(salary, -2)) # Round to nearest 100, min 30k
        
        # Calculate demand score based on job characteristics (rule-based for ML target)
        # High demand: Remote, contains hot skills (PySpark, Kubernetes, Python, React), high industry demand
        demand_points = 0
        if job_type == "Remote":
            demand_points += 2
        if "Python" in skills or "PySpark" in skills or "Kubernetes" in skills or "React" in skills:
            demand_points += 2
        if experience in ["Entry-level", "Mid-level"]: # More applicant volume
            demand_points += 1
        if industry in ["Tech", "Finance"]:
            demand_points += 1
            
        if demand_points >= 5:
            demand_score = "High"
        elif demand_points >= 3:
            demand_score = "Medium"
        else:
            demand_score = "Low"
            
        post_date = start_date + timedelta(days=random.randint(0, 365))
        
        jobs.append({
            "job_id": str(uuid.uuid4()),
            "job_title": title,
            "company": company,
            "location": location,
            "experience_level": experience,
            "job_type": job_type,
            "salary": salary,
            "skills": skills,
            "industry": industry,
            "post_date": post_date.strftime("%Y-%m-%d"),
            "demand_score": demand_score
        })
        
    return jobs

if __name__ == "__main__":
    import os
    print("Generating job postings...")
    jobs = generate_job_postings(100000)
    
    os.makedirs("backend/data", exist_ok=True)
    output_path = "backend/data/jobs_large.json"
    
    with open(output_path, "w") as f:
        json.dump(jobs, f, indent=2)
        
    print(f"Successfully generated {len(jobs)} records in {output_path}")
