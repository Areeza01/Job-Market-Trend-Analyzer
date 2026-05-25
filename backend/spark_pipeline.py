import os
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, avg, count, round as spark_round, desc, when, lit

def run_spark_pipeline():
    print("Starting Spark Session...")
    spark = SparkSession.builder \
        .appName("JobMarketTrendAnalyzer") \
        .config("spark.driver.memory", "4g") \
        .master("local[*]") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")
    
    input_file = "backend/data/jobs_large.json"
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input data file {input_file} not found. Please run data_generator.py first.")
        
    print(f"Loading dataset from {input_file}...")
    df = spark.read.option("multiLine", "true").json(input_file)
    
    # 1. Cleaning & Preprocessing
    print("Preprocessing data...")
    # Drop rows with critical null fields (if any)
    cleaned_df = df.filter(
        col("job_title").isNotNull() & 
        col("salary").isNotNull() & 
        col("skills").isNotNull()
    )
    
    # Standardize salary field
    cleaned_df = cleaned_df.withColumn("salary", col("salary").cast("double"))
    
    # 2. Aggregations & Analytics
    print("Computing aggregations...")
    output_dir = "backend/data/processed"
    os.makedirs(output_dir, exist_ok=True)
    
    # A. Overall Stats
    total_jobs = cleaned_df.count()
    avg_salary = cleaned_df.select(avg("salary")).first()[0]
    remote_jobs = cleaned_df.filter(col("job_type") == "Remote").count()
    remote_pct = (remote_jobs / total_jobs) * 100 if total_jobs > 0 else 0
    
    overall_stats = {
        "total_jobs": total_jobs,
        "average_salary": round(avg_salary, 2),
        "remote_percentage": round(remote_pct, 2)
    }
    with open(f"{output_dir}/overall_stats.json", "w") as f:
        json.dump(overall_stats, f)
        
    # B. Average Salary by Job Title & Experience Level
    print("Analyzing Salary by Title and Experience...")
    salary_by_title_exp = cleaned_df.groupBy("job_title", "experience_level") \
        .agg(
            spark_round(avg("salary"), 2).alias("avg_salary"),
            count("job_id").alias("job_count")
        ) \
        .orderBy("job_title", "experience_level") \
        .collect()
        
    title_exp_list = [row.asDict() for row in salary_by_title_exp]
    with open(f"{output_dir}/salary_by_title_exp.json", "w") as f:
        json.dump(title_exp_list, f, indent=2)

    # C. Skill Popularity and Average Salary
    print("Analyzing Skills (Popularity & Salaries)...")
    exploded_skills_df = cleaned_df.withColumn("skill", explode(col("skills")))
    
    skills_analysis = exploded_skills_df.groupBy("skill") \
        .agg(
            count("job_id").alias("frequency"),
            spark_round(avg("salary"), 2).alias("avg_salary")
        ) \
        .orderBy(desc("frequency")) \
        .collect()
        
    skills_list = [row.asDict() for row in skills_analysis]
    with open(f"{output_dir}/skills_analysis.json", "w") as f:
        json.dump(skills_list, f, indent=2)

    # D. Industry Job Share and Remote Work Percentage
    print("Analyzing Industry metrics...")
    industry_metrics = cleaned_df.groupBy("industry") \
        .agg(
            count("job_id").alias("job_count"),
            spark_round(avg("salary"), 2).alias("avg_salary"),
            spark_round(
                (count(when(col("job_type") == "Remote", 1)) / count("job_id")) * 100, 2
            ).alias("remote_percentage")
        ) \
        .orderBy(desc("job_count")) \
        .collect()
        
    industry_list = [row.asDict() for row in industry_metrics]
    with open(f"{output_dir}/industry_metrics.json", "w") as f:
        json.dump(industry_list, f, indent=2)

    # E. Salary Distribution (Histograms)
    print("Computing salary bands...")
    salary_bins = cleaned_df.withColumn(
        "salary_band",
        when(col("salary") < 60000, "Under $60k")
        .when((col("salary") >= 60000) & (col("salary") < 90000), "$60k - $90k")
        .when((col("salary") >= 90000) & (col("salary") < 120000), "$90k - $120k")
        .when((col("salary") >= 120000) & (col("salary") < 150000), "$120k - $150k")
        .when((col("salary") >= 150000) & (col("salary") < 180000), "$150k - $180k")
        .otherwise("Over $180k")
    )
    
    salary_distribution = salary_bins.groupBy("salary_band") \
        .count() \
        .collect()
        
    salary_dist_list = [row.asDict() for row in salary_distribution]
    # Order salary bands logically
    band_order = ["Under $60k", "$60k - $90k", "$90k - $120k", "$120k - $150k", "$150k - $180k", "Over $180k"]
    salary_dist_ordered = sorted(salary_dist_list, key=lambda x: band_order.index(x["salary_band"]) if x["salary_band"] in band_order else 99)
    
    with open(f"{output_dir}/salary_distribution.json", "w") as f:
        json.dump(salary_dist_ordered, f, indent=2)

    # 3. Export Cleaned Dataset for Scikit-Learn ML Training
    print("Exporting ML dataset...")
    # Select columns useful for ML training and save as JSON
    ml_data_df = cleaned_df.select("job_title", "location", "experience_level", "job_type", "salary", "skills", "industry", "demand_score")
    # For Scikit-Learn training, we will just export as a single consolidated file
    ml_data_list = [row.asDict() for row in ml_data_df.collect()]
    with open(f"{output_dir}/ml_training_data.json", "w") as f:
        json.dump(ml_data_list, f)

    print("Spark pipeline completed successfully!")
    spark.stop()

if __name__ == "__main__":
    run_spark_pipeline()
