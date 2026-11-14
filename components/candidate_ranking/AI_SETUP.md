# 🤖 A.I. Skills analysis settings

## Overview

Candidate Analysis includes **AI candidate skills analysis** using **OpenAI GPT-4.1-nano** (fixed model)). That's how it works:

- **Automatic analysis** of candidates &apos; skills
- **Assess relevance** of skills for a particular vacancy
- **Determine the level of ownership** (Junior/Middle/Senior/Expert)
- **Keep the results** in the database for reuse

## 🚀 Rapid settings

### 1. OpenAI API Key

1. **Register** to [openAI Platform](https://platform.openai.com)/)
2. **Go to [API Keys](https://platform.openai.com/api-keys))
3. ** Create a new key** with rights to GPT-4.1-nano
4. ** Copy key** (starts with `sk-`)

### 2. Settings of the environment variables

#### For Docker Compose:

Create the `.env` file at the root of the project:

```bash
# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key-here

# HeadHunter API (already set)
HH_CLIENT_ID=your_hh_client_id_here
HH_CLIENT_SECRET=your_hh_client_secret_here
```

#### For local installation:

```bash
export OPENAI_API_KEY="sk-your-openai-api-key-here"
```

### 3. Start the system

```bash
# Stop existing services
docker-compose down

# Run with new services.
docker-compose up -d
```

## 🔧 AI analysis configuration

### `config/settings.yaml` settings:

```yaml
ai_analysis:
  openai_api_key: "" # To be filled in from variable environments
  model: "gpt-4.1-nano" # OpenAI model
  max_tokens: 2000 # Maximum number of currents
  temperature: 0.3 # Creativeity (0.0-1.0)
  timeout: 60 # Request times in seconds
  retry_attempts: 3 # Number of repeated attempts
  
  # Analysis gaps
  prompts:
    skill_analysis: |
      "{job_title)}".
      
      Candidates &apos; skills: {skills}
      Description of experience: {experience}
      Search request: {search_query}
      
      For each skill, rate:
      1. Vacancy relevance (0-1)
      2. Level of ownership (Junior/Middle/Senior/Expert)
      3. Years of experience (if possible)
      4. Confidence in evaluation (0-1)
      
      Response format: JSON array of objects with fields skill_name, relevance_score, proficiency_level, years_experience,ai_confidence
    
    overall_assessment: |
      Assess the overall suitability of the candidate for the vacancy. &quot; {job_title}".
      
      Skills analysis: {skill_analysis}
      Search request: {search_query}
      
      Give an overall assessment (0-1) and a brief summary (2-3 proposals)).
      
      Response format: JSON object with overall_score fields, submary
```

## 📊 How AI analysis works

### 1. Analysis process

1. ** Search for candidates** on HeadHunter API
2. ** Check** available in the database
3. **AI analysis** new candidates (if not analysed))
4. ** Conservation** of database results
5. ** Earning** based on AI assessment

### 2. The parameters to be analysed

#### Skills:
- **Relevancy** (0-1) - how much skill is suitable for a vacancy
- ** Level of ownership** - Junior/Middle/Senior/Expert
- ** Years of experience** - evaluation of experience with skills
- ** AI** (0-1) - how sure AI is of the evaluation

#### Overall assessment:
- ** Total **/ (0-1) - Total suitability
- ** Summary** - Brief description of strengths and weaknesses

### 3. Example of result

```json
{
  "candidate_id": "12345",
  "skill_analysis": [
    {
      "skill_name": "Python",
      "relevance_score": 0.9,
      "proficiency_level": "Senior",
      "years_experience": 5,
      "ai_confidence": 0.85,
      "analysis_timestamp": "2024-01-15T10:30:00"
    },
    {
      "skill_name": "Django",
      "relevance_score": 0.7,
      "proficiency_level": "Middle",
      "years_experience": 3,
      "ai_confidence": 0.75,
      "analysis_timestamp": "2024-01-15T10:30:00"
    }
  ],
  "overall_score": 0.82,
  "analysis_summary": "The candidate has a strong experience in Python development with a deep knowledge of the framework. Suitable for a senior position.",
  "processing_time": 2.3
}
```

## 🎯 A.I. Ran

### New ranking algorithm:

1. **AI Skills Assessment** (40%) - GPT-4.1-nano
2. **Filter compliance** (30%) - geography, experience, salary
3. ** Actuariality** (20%) - freshness of summary
4. **Profile completeness** (10%) - photo, description, etc.

### Calculation formula:

```
Total= (AI_evaluation× 0.4) + (Filters× 0.3) + (Relevance× 0.2) + (Fullness× 0.1)
```

## 📈 Statistics and monitoring

### Available statistics:

- ** Total number of candidates** in the database
- **Number of candidates analysed**
- ** Covering AI analysis** (per cent)
- ** Average AI rating** for all candidates
- ** Total skills** in the database

### View statistics:

1. Open a web interface: http://localhost:8501
2. In the side panel, find the section on database statistics.
3. Look at the metrics and the progress bar.

## 🔍 Debugging and monitoring

### Audit of AI analysis:

```bash
# Health audit of AI service
curl http://localhost:8005/health

# The configuration check
curl http://localhost:8005/config

# Test analysis (through API Gateway)
curl -X POST http://localhost:8000/ai-analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": "test",
    "search_query": "Python Developer",
    "skills": ["Python", "Django", "PostgreSQL"],
    "experience_description": "5 Years of development experience"
  }'
```

### AI service logs:

```bash
# Docker
docker logs hrhelp-ai_analysis-1

# Local
tail -f logs/ai-analysis-service.log
```

### Challenges and solutions:

#### 1. "OPENAI_API_KEY not installed"
```bash
# Check the variable environment
echo $OPENAI_API_KEY

# Make sure the key starts with the sk--
```

#### 2. "Rate limit exceeded"
```bash
# Zoom in the interval between requests
# In config/settings.yaml:
ai_analysis:
  timeout: 120 # Increase timeout
```

#### 3. "Model not found"
```bash
# Check the model's accessibility
# Make sure you have access to GPT-4.1-nano
```

## 💰 Value of use

### OpenAI API tariffs (2025):

- **GPT-4.1-nano**: ~ $0.01 for 1K currents (entry) + ~$0.02 for the 1K currents)
- **Medical analysis**: ~1000-2000 currents for candidate
- ** Cost of analysis**: ~ $0.015-0.03 for candidate

### Cost optimization:

1. **Cashing of results** - analysis performed only for new candidates
2. ** Settings max_tokens** - Limit the response length
3. **Batch analysis** - group requests for savings

## 🔮 Development plans

### Future improvements:

- [ ] ** Support to other AI models** (Claude, Gemini)
- [ ] **Summary Analysis** (extracting skills from the text)
- [ ] ** Machine training** to improve ratings
- [ ] **Personalization** for specific companies
- [ ] **Analysis soft scills** (communications, leadership)
- [ ] ** Integration with ATS** (Applicant Trading Systems)

## 📚 Additional resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [GPT-4 Technical Report](https://arxiv.org/abs/2303.08774)
- [HeadHunter API Documentation](https://github.com/hhru/api)

---

**AI skills analysis** makes Candidate Analysis a smart system for finding candidates! 🚀