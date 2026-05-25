const API_BASE = ""; // Relative paths will work automatically since served on the same host

// Global Chart References
let skillsChart = null;
let salaryChart = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  loadMetadata();
  loadInsights();
  loadJobs();
  
  // Bind Event Listeners
  document.getElementById("predictor-form").addEventListener("submit", handlePrediction);
  document.getElementById("generate-roadmap-btn").addEventListener("click", handleRoadmap);
  
  document.getElementById("search-title").addEventListener("input", filterJobs);
  document.getElementById("filter-industry").addEventListener("change", filterJobs);
  document.getElementById("filter-type").addEventListener("change", filterJobs);
});

// Check API Connection Status
async function checkHealth() {
  const badge = document.getElementById("status-badge");
  const text = document.getElementById("status-text");
  
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      badge.className = "status-badge online";
      text.innerText = "API Online";
    } else {
      throw new Error();
    }
  } catch (err) {
    badge.className = "status-badge offline";
    text.innerText = "Demo Mode";
  }
}

// Load Metadata options (e.g. available skills for checkboxes)
async function loadMetadata() {
  const grid = document.getElementById("skills-grid");
  
  try {
    const res = await fetch(`${API_BASE}/api/metadata`);
    if (res.ok) {
      const data = await res.json();
      const skills = data.skills || [];
      
      grid.innerHTML = "";
      skills.forEach(skill => {
        const label = document.createElement("label");
        label.className = "skill-checkbox-label";
        label.innerHTML = `
          <input type="checkbox" name="skills" value="${skill}">
          <span>${skill}</span>
        `;
        grid.appendChild(label);
      });
    }
  } catch (err) {
    console.error("Failed to load skills metadata, using defaults.");
    const defaultSkills = ["Python", "SQL", "Git", "JavaScript", "Docker", "PySpark", "AWS", "React", "Machine Learning", "Kubernetes"];
    grid.innerHTML = "";
    defaultSkills.forEach(skill => {
      const label = document.createElement("label");
      label.className = "skill-checkbox-label";
      label.innerHTML = `
        <input type="checkbox" name="skills" value="${skill}">
        <span>${skill}</span>
      `;
      grid.appendChild(label);
    });
  }
}

// Load PySpark aggregated metrics and render charts
async function loadInsights() {
  try {
    const res = await fetch(`${API_BASE}/api/insights`);
    if (res.ok) {
      const data = await res.json();
      
      // Update top stats
      document.getElementById("stat-total").innerText = data.overall.total_jobs.toLocaleString();
      document.getElementById("stat-salary").innerText = `$${Math.round(data.overall.average_salary).toLocaleString()}`;
      document.getElementById("stat-remote").innerText = `${data.overall.remote_percentage}%`;
      
      // Render Charts
      renderSkillsChart(data.skills);
      renderSalaryChart(data.salary_distribution);
    }
  } catch (err) {
    console.error("Could not fetch aggregated insights, running in offline demo mode.");
    
    // Fallback Mock Data
    document.getElementById("stat-total").innerText = "100,000";
    document.getElementById("stat-salary").innerText = "$98,400";
    document.getElementById("stat-remote").innerText = "30.5%";
    
    const mockSkills = [
      { skill: "Python", frequency: 32000 },
      { skill: "SQL", frequency: 28500 },
      { skill: "Git", frequency: 25000 },
      { skill: "JavaScript", frequency: 22000 },
      { skill: "Docker", frequency: 18000 },
      { skill: "PySpark", frequency: 15400 },
      { skill: "AWS", frequency: 15000 }
    ];
    
    const mockDist = [
      { salary_band: "Under $60k", count: 8500 },
      { salary_band: "$60k - $90k", count: 28200 },
      { salary_band: "$90k - $120k", count: 35400 },
      { salary_band: "$120k - $150k", count: 18300 },
      { salary_band: "$150k - $180k", count: 7200 }
    ];
    
    renderSkillsChart(mockSkills);
    renderSalaryChart(mockDist);
  }
}

// Render the Skill Frequencies Chart (Horizontal Bar Chart)
function renderSkillsChart(skillsData) {
  const ctx = document.getElementById("skillsChart").getContext("2d");
  
  if (skillsChart) skillsChart.destroy();
  
  const labels = skillsData.map(d => d.skill);
  const frequencies = skillsData.map(d => d.frequency);
  
  // Custom Gradient
  const grad = ctx.createLinearGradient(0, 0, 400, 0);
  grad.addColorStop(0, "#06b6d4"); // Cyan
  grad.addColorStop(1, "#8b5cf6"); // Purple
  
  skillsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Job Count Reference",
        data: frequencies,
        backgroundColor: grad,
        borderRadius: 5,
        borderWidth: 0
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8" }
        },
        y: {
          grid: { display: false },
          ticks: { color: "#cbd5e1" }
        }
      }
    }
  });
}

// Render the Salary Distribution Chart (Doughnut Chart)
function renderSalaryChart(salaryData) {
  const ctx = document.getElementById("salaryChart").getContext("2d");
  
  if (salaryChart) salaryChart.destroy();
  
  const labels = salaryData.map(d => d.salary_band);
  const counts = salaryData.map(d => d.count);
  
  salaryChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        backgroundColor: [
          "#0284c7", // Sky
          "#0d9488", // Teal
          "#10b981", // Emerald
          "#8b5cf6", // Purple
          "#ec4899", // Pink
          "#f59e0b"  // Yellow
        ],
        borderWidth: 1,
        borderColor: "#131924"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: {
            color: "#94a3b8",
            font: { size: 10 }
          }
        }
      }
    }
  });
}

// Load and Filter Jobs Index
async function loadJobs(title = "", industry = "", type = "") {
  const container = document.getElementById("jobs-list");
  
  try {
    let url = `${API_BASE}/api/jobs?`;
    if (title) url += `title=${encodeURIComponent(title)}&`;
    if (industry) url += `industry=${encodeURIComponent(industry)}&`;
    if (type) url += `type=${encodeURIComponent(type)}&`;
    
    const res = await fetch(url);
    if (!res.ok) throw new Error();
    
    const data = await res.json();
    displayJobs(data);
  } catch (err) {
    // Mock Fallback
    const mockJobs = [
      { job_title: "Senior Data Scientist", company: "Google", location: "Remote", experience_level: "Senior", job_type: "Remote", salary: 168000, industry: "Tech", demand_score: "High", skills: ["Python", "PySpark", "Machine Learning"] },
      { job_title: "Software Engineer", company: "Meta", location: "San Francisco, CA", experience_level: "Mid-level", job_type: "Onsite", salary: 115000, industry: "Tech", demand_score: "Medium", skills: ["Java", "SQL", "Git", "Docker"] },
      { job_title: "Cloud Architect", company: "Amazon", location: "Seattle, WA", experience_level: "Lead", job_type: "Hybrid", salary: 185000, industry: "Tech", demand_score: "High", skills: ["AWS", "Kubernetes", "Docker"] }
    ];
    
    let filtered = mockJobs;
    if (title) filtered = filtered.filter(j => j.job_title.toLowerCase().includes(title.toLowerCase()));
    if (industry) filtered = filtered.filter(j => j.industry === industry);
    if (type) filtered = filtered.filter(j => j.job_type === type);
    
    displayJobs(filtered);
  }
}

function displayJobs(jobsList) {
  const container = document.getElementById("jobs-list");
  container.innerHTML = "";
  
  if (jobsList.length === 0) {
    container.innerHTML = `<div class="job-card" style="text-align: center; color: var(--text-muted);">No job listings match the filter parameters.</div>`;
    return;
  }
  
  jobsList.forEach(job => {
    const card = document.createElement("div");
    card.className = "job-card";
    
    const demandClass = job.demand_score.toLowerCase() === "high" ? "demand-high" : (job.demand_score.toLowerCase() === "medium" ? "demand-medium" : "demand-low");
    const skillsList = (job.skills || []).map(s => `<span class="job-skill-chip">${s}</span>`).join("");
    
    card.innerHTML = `
      <div class="job-card-header">
        <div>
          <h4 class="job-title">${job.job_title}</h4>
          <span class="company-name">${job.company} • ${job.location}</span>
        </div>
        <span class="job-salary-tag">$${job.salary.toLocaleString()}</span>
      </div>
      <div class="job-card-details">
        <span>${job.industry}</span>
        <span>•</span>
        <span>${job.job_type}</span>
        <span>•</span>
        <span>${job.experience_level}</span>
        <span>•</span>
        <span class="demand-tag ${demandClass}">${job.demand_score} Demand</span>
      </div>
      <div class="job-salary-tag" style="font-size: 11px; margin-top: 10px; color: var(--text-muted);">REQUIRED CAPABILITIES:</div>
      <div class="job-skills-wrap">
        ${skillsList}
      </div>
    `;
    container.appendChild(card);
  });
}

function filterJobs() {
  const title = document.getElementById("search-title").value;
  const industry = document.getElementById("filter-industry").value;
  const type = document.getElementById("filter-type").value;
  loadJobs(title, industry, type);
}

// Handle ML Prediction Submission
async function handlePrediction(e) {
  e.preventDefault();
  
  const title = document.getElementById("job-title").value;
  const exp = document.getElementById("exp-level").value;
  const type = document.getElementById("job-type").value;
  const ind = document.getElementById("industry").value;
  
  const checkedBoxes = document.querySelectorAll('input[name="skills"]:checked');
  const selectedSkills = Array.from(checkedBoxes).map(cb => cb.value);
  
  const payload = {
    job_title: title,
    experience_level: exp,
    job_type: type,
    industry: ind,
    skills: selectedSkills
  };
  
  try {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      const data = await res.json();
      showPredictionResult(data.predicted_salary, data.predicted_demand_score, data.feature_importance);
    }
  } catch (err) {
    console.error("Prediction failed, returning model mock values.");
    // Fallback simulation
    const simulatedSalary = 105000 + (selectedSkills.length * 5000) + (exp === "Senior" ? 30000 : (exp === "Lead" ? 50000 : 0));
    const simulatedDemand = selectedSkills.includes("PySpark") || selectedSkills.includes("Machine Learning") ? "High" : "Medium";
    
    const simulatedImp = [
      { feature: "Experience Level", importance: 0.42 },
      { feature: "Skills Coefficients", importance: 0.31 },
      { feature: "Industry Segment", importance: 0.18 }
    ];
    showPredictionResult(simulatedSalary, simulatedDemand, simulatedImp);
  }
}

function showPredictionResult(salary, demand, importances) {
  const panel = document.getElementById("prediction-result");
  panel.classList.remove("hidden");
  
  document.getElementById("predicted-salary").innerText = `$${Math.round(salary).toLocaleString()}`;
  document.getElementById("predicted-demand").innerText = `${demand}`;
  
  const list = document.getElementById("feature-list");
  list.innerHTML = "";
  
  const arrayImp = Array.isArray(importances) ? importances : Object.entries(importances).map(([k, v]) => ({ feature: k, importance: v }));
  
  arrayImp.slice(0, 4).forEach(imp => {
    const item = document.createElement("div");
    item.className = "feature-item";
    item.innerHTML = `
      <span class="feature-name">${imp.feature}</span>
      <span class="feature-value">${Math.round(imp.importance * 100)}%</span>
    `;
    list.appendChild(item);
  });
  
  // Smooth scroll to details
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Handle AI Career Roadmap Generation
async function handleRoadmap() {
  const role = document.getElementById("roadmap-role").value;
  
  try {
    const res = await fetch(`${API_BASE}/api/roadmap?role=${encodeURIComponent(role)}`, {
      method: "POST"
    });
    
    if (res.ok) {
      const data = await res.json();
      showRoadmapResult(data.role, data.milestones);
    }
  } catch (err) {
    console.error("Failed to generate roadmap, using mock timeline.");
    const mockMilestones = [
      { title: "Stage 1: Core Fundamentals", description: "Master basics, syntax, data storage structures, and query parameters.", skills: ["Python", "SQL"] },
      { title: "Stage 2: Big Data Operations", description: "Establish scalable distributed batch processing routines.", skills: ["PySpark", "Hadoop"] },
      { title: "Stage 3: Cloud Architectures", description: "Deploy automated dockerized microservices.", skills: ["Docker", "Kubernetes", "AWS"] }
    ];
    showRoadmapResult(role, mockMilestones);
  }
}

function showRoadmapResult(role, milestones) {
  const panel = document.getElementById("roadmap-output");
  panel.classList.remove("hidden");
  
  document.getElementById("roadmap-title").innerText = `${role} Career Development Matrix`;
  
  const container = document.getElementById("roadmap-milestones");
  container.innerHTML = "";
  
  milestones.forEach((m, idx) => {
    const item = document.createElement("div");
    item.className = "milestone-item";
    
    const skillsHtml = (m.skills || []).map(s => `<span class="roadmap-skill-badge">${s}</span>`).join("");
    
    item.innerHTML = `
      <h4>Step ${idx + 1}: ${m.title || m.stage}</h4>
      <p>${m.description}</p>
      <div class="milestone-skills">
        ${skillsHtml}
      </div>
    `;
    container.appendChild(item);
  });
  
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
