"""
CandidateRanking - Streamlit Frontend

Minimum UI flow: A vacancy rate.
"""

import os
import requests
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Optional

# Page configuration
st.set_page_config(
    page_title='CandidateRanking — Responding TOP',
    page_icon="👑",
    layout="wide",
)

# Core URL Gateway (in docker and local)
IS_DOCKER = os.getenv("DOCKER_ENV") == "true"
API_BASE_URL = "http://gateway:8088" if IS_DOCKER else "http://localhost:8088"


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.base_url}{endpoint}"
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code >= 400:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                
                # Improved error reports
                if resp.status_code == 401:
                    st.error('🔐 **Authorization error**: You need to set the OAuth HH API tokens in the configuration file.')
                elif resp.status_code == 403:
                    st.error("🚫 **Access prohibited**: Not enough rights. Make sure you have the employer's rights to view the response to the vacancy.")
                elif resp.status_code == 404:
                    st.error('📭 **Not found**: Vacansia does not exist or responses are not available.')
                elif resp.status_code == 429:
                    st.error('🚦 **Overlimit**: Too many HH API requests. Try later.')
                else:
                    st.error(f"Error of API {resp.status_code}: {detail}")
                return None
            return resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Network error: {e}")
            return None


client = ApiClient(API_BASE_URL)


def format_experience_months(months: Optional[int]) -> str:
    if not months or months <= 0:
        return "—"
    years = months // 12
    rest = months % 12
    return f"{years} (Signed) N. G. {rest} No, sir." if years else f"{months} No, sir."


def candidate_card(c: Dict[str, Any]) -> None:
    'Presentation of the candidate card with full multi-agent AI analysis'
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            if c.get("photo_url"):
                st.image(c["photo_url"], width=100)
            else:
                st.image("https://via.placeholder.com/100x100?text=👤", width=100)
        with col2:
            title = c.get("title") or 'Post not specified'
            name = c.get("name") or 'Candidature'
            st.subheader(f"👤 {name}")
            st.write(f"**Durability:** {title}")

            # Reference to executive summary and date of update
            link_col, upd_col, score_col = st.columns([1, 1, 1])
            with link_col:
                if c.get("url"):
                    st.link_button('📄 Executive summary', c["url"])
            with upd_col:
                if c.get("updated_at"):
                    try:
                        upd = datetime.fromisoformat(c["updated_at"].replace("Z", "+00:00"))
                        st.caption(f"🕒 Updated: {upd.strftime('%d.%m.%Y')}")
                    except Exception:
                        pass
            with score_col:
                if c.get("score") is not None:
                    score = float(c.get("score") or 0)
                    color = "green" if score >= 80 else ("orange" if score >= 50 else "red")
                    st.markdown(f"**🤖 AI – Evaluation:** :{color}[{score:.1f}%]")
            
            st.markdown("---")

            # Basic information
            meta = []
            area_name = c.get("area", {}).get("name")
            if area_name:
                meta.append(f"🏙️ {area_name}")
            exp_months = (c.get("experience") or {}).get("total_months")
            if exp_months is not None:
                meta.append(f"🗓️ Experience: {format_experience_months(exp_months)}")
            sal = c.get("salary") or {}
            if sal.get("from") or sal.get("to"):
                if sal.get("from") and sal.get("to"):
                    meta.append(f"💰 {sal['from']:,}–{sal['to']:,} {sal.get('currency','RUR')}")
                elif sal.get("from"):
                    meta.append(f"💰 from {sal['from']:,} {sal.get('currency','RUR')}")
                elif sal.get("to"):
                    meta.append(f"💰 up to {sal['to']:,} {sal.get('currency','RUR')}")
            if meta:
                st.write(" · ".join(meta))

            # Skills
            skills = c.get("skills") or []
            if skills:
                st.caption('** Skills:** ' + ", ".join(skills[:10]) + (" …" if len(skills) > 10 else ""))

            # Last job
            last_work = c.get("last_work")
            if last_work and last_work.get("position") and last_work.get("company"):
                st.write(f"** Last place of work:** {last_work['position']} in {last_work['company']}")

            # == sync, corrected by elderman == @elder_man
            analysis_status = c.get("analysis_status")
            multi_agent_data = c.get("multi_agent_data")
            
            if c.get("score") and analysis_status == "completed" and multi_agent_data and isinstance(multi_agent_data, dict):
                st.markdown("---")
                st.subheader('🤖 Multi-agent AI analysis')
                
                # == sync, corrected by elderman == @elder_man
                master_report = multi_agent_data.get("master_report", {})
                if master_report and isinstance(master_report, dict):
                    overall_score = master_report.get("overall_score", 0.0)
                    recommendation = master_report.get("recommendation", 'No recommendation')
                    
                    # Outcome evaluation and recommendation
                    score_color = "green" if overall_score >= 80 else "orange" if overall_score >= 60 else "red"
                    st.markdown(f"*# * Total rating:** *{score_color}[{overall_score:.1f}%]")
                    st.success(f"**📋 Recommendation:** {recommendation}")
                    
                    # == sync, corrected by elderman == @elder_man
                    master_assessment = master_report.get("master_assessment", "")
                    if master_assessment:
                        with st.expander('🧠 **Expert opinion by AI Coordinator**', expanded=True):
                            st.markdown(master_assessment)
                    
                    # ===AGENCY AGENCIES (INTERACTIVE) ===
                    individual_scores = master_report.get("individual_scores", {})
                    if individual_scores:
                        with st.expander('👥 **Summary estimates of all agents**', expanded=True):
                            # Create columns for beautiful display
                            for i, (agent_name, agent_score) in enumerate(individual_scores.items()):
                                if i % 2 == 0:  # Every second line is in the columns.
                                    cols = st.columns(2)
                                
                                col_idx = i % 2
                                with cols[col_idx]:
                                    agent_score_color = "green" if agent_score >= 80 else "orange" if agent_score >= 60 else "red"
                                    # Remove encoding artifacts
                                    clean_agent_name = str(agent_name).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                    st.markdown(f"**{clean_agent_name}:** :{agent_score_color}[{agent_score:.1f}%]")
                    
                    # === AGENCIES (INTERACTIVE EXPANDER'S)) ===
                    agent_reports = multi_agent_data.get("agent_reports", [])
                    if agent_reports and len(agent_reports) > 0:
                        st.markdown("---")
                        st.markdown('### 🔍 **Children &apos; s records**')
                        
                        # Interactive extander's for each agent
                        for i, report in enumerate(agent_reports):
                            if not isinstance(report, dict):
                                continue
                                
                            agent_name = report.get("agent_name", f"Agent {i+1}")
                            agent_score = report.get("score", 0)
                            status = report.get("status", "unknown")
                            summary = report.get("summary", 'No description')
                            
                            # Remove encoding artifacts
                            clean_agent_name = str(agent_name).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                            clean_summary = str(summary).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                            
                            # Defining color and emoji status
                            status_mapping = {
                                "pass": ("green", "✅"),
                                "warning": ("orange", "⚠️"),
                                "fail": ("red", "❌"),
                                "error": ("red", "🔥")
                            }
                            status_color, status_emoji = status_mapping.get(status, ("gray", "❓"))
                            
                            # INTERACTIVE EXPANDER FOR EVERY AGENCY
                            with st.expander(
                                f"{status_emoji} **{clean_agent_name}** — {agent_score:.1f}% — _{clean_summary}_",
                                expanded=False  # By default
                            ):
                                # Detailed information from the agent
                                details = report.get("details", [])
                                red_flags = report.get("red_flags", [])
                                positive_points = report.get("positive_points", [])
                                recommendations = report.get("recommendations", [])
                                
                                if details:
                                    st.markdown('**🔍 Detailed analysis:**')
                                    for detail in details:
                                        clean_detail = str(detail).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        st.markdown(f"• {clean_detail}")
                                
                                if red_flags:
                                    st.markdown('**🚩 Problems identified:**')
                                    for flag in red_flags:
                                        clean_flag = str(flag).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        st.error(f"• {clean_flag}")
                                
                                if positive_points:
                                    st.markdown('**✅ Strong parties:**')
                                    for point in positive_points:
                                        clean_point = str(point).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        st.success(f"• {clean_point}")
                                
                                if recommendations:
                                    st.markdown('**💡 Recommendations:**')
                                    for rec in recommendations:
                                        clean_rec = str(rec).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        st.info(f"• {clean_rec}")
                    
                    # == sync, corrected by elderman == @elder_man
                    relevance_boost = c.get("relevance_boost", 0)
                    if relevance_boost and relevance_boost > 0:
                        st.info(f"🎯 **Bonus for the relevance of the search:** +{relevance_boost:.1f}%")
                    
                    # == sync, corrected by elderman == @elder_man
                    active_agents = multi_agent_data.get("active_agents", [])
                    total_time = multi_agent_data.get("total_processing_time", 0)
                    
                    with st.expander('🔢 **Formula and technical details**', expanded=False):
                        formula_text = f"""
🧮 FORM OF CALCULATION:
Total estimate = Average arithmetical(s){len(active_agents)} (Agents) + Bonus of relevance

🤖 ACTIVE AGENCIES ({len(active_agents)}):
• Analysis of entry requirements
• Technical skills and experience  
• Level of mastery
• Quality of the summary as a document
• Professional experience
• Formation and structure
• Detecting anomalies and inconsistencies

⚡ Processing time: {total_time:.3f}c
                        """
                        st.code(formula_text, language="text")
            
            # FALLBACK: if multi-agent data are not available
            elif c.get("score"):
                st.markdown("---")
                st.subheader('🤖 AI Analysis')
                
                if analysis_status != "completed":
                    st.warning('⚠️ Multi-agent analysis not completed or not available')
                
                # Summary of the analysis
                analysis_summary = c.get("analysis_summary")
                if analysis_summary and analysis_summary != 'Summary analysis not available':
                    st.info(f"**📝 Summary of the analysis:** {analysis_summary}")
                
                # Justification AI
                reasoning = c.get("reasoning")
                if reasoning:
                    st.subheader('🧠 Justification AI')
                    st.write(reasoning)

        st.markdown("---")


def main():
    st.title('👑 CandidateRanking is a job-reacting TAX')
    st.markdown("Insert a link to the hh.ru vacancy. The service will upload the responses, do AI's analysis, and build the TOP.")
    
    # Show settings information
    with st.expander('ℹ️ System settings', expanded=False):
        st.markdown('\n        **/ For the operation of the system:**\n        1. **OAuth currents HH API** for access to responses to your vacancies\n        2. **OpenAI API Key** - for AI analysis of the summaries of candidates\n        \n        **Construction:**\n        - Copy `config/settings.yaml.template` in `config/settings.yaml`\n        - Fill in fields`hh_api.client_id`, `hh_api.client_secret`, `hh_api.user_tokens.access_token`\n        - Add OpenAI key to `ai_analysis.openai_api_key`\n        \n        **Important:** The system only works with vacancies that belong to your employer account on hh.ru\n        ')

    health = client.request("GET", "/health")
    if not health:
        st.error('Gateway not available. Make sure the system is running (docker-composition up -d --build)).')
        st.stop()

    with st.form("vacancy_form"):
        vacancy_url = st.text_input('Reference to vacancy', placeholder="https://hh.ru/vacancy/123456789")
        limit = st.slider('How many candidates to show on the TOP', 3, 50, 10, 1)
        submitted = st.form_submit_button('Build a TAP on the responses')

    if submitted:
        if not vacancy_url.strip():
            st.error('Please specify the vacancy reference')
            st.stop()

        with st.spinner('Upload the feedback, analyze, build the TOP...'):
            payload = {"vacancy_url": vacancy_url.strip(), "limit": int(limit)}
            resp = client.request("POST", "/vacancy/top", json=payload)
            if not resp:
                st.error('Unable to obtain a TAP for a vacancy')
                st.stop()

        vacancy_id = resp.get("vacancy_id", "")
        total_responses = resp.get("total_responses", 0)
        candidates = resp.get("candidates", [])

        st.subheader(f"TIP of candidates (vacanium) {vacancy_id})")
        if not candidates:
            if total_responses == 0:
                st.info('📭 **This vacancy has not yet been answered** or you do not have access to it.')
                st.markdown("\n                ** Possible causes:**\n                - The vacancy doesn't belong to your employer's account  \n                - OAuth currents are wrong.\n                - Vacation not active or withdrawn from publication\n                - There's really no response yet.\n                ")
            else:
                st.warning('⚠️ Unable to process feedback. Try later.')
        else:
            # Representation of candidates
            for i, cand in enumerate(candidates, 1):
                score = cand.get("score", 0) or 0
                name = cand.get("name", 'Candidature')
                title = cand.get("title", 'Post not specified')
                score_color = "🟢" if score >= 80 else ("🟡" if score >= 50 else "🔴")
                
                st.markdown(f"### #{i} {score_color} **{name}** — {title} (AI: {score:.1f}%)")
                candidate_card(cand)
                st.markdown("---")

            # Table and exports
            try:
                import pandas as pd
                df = pd.DataFrame(candidates)
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button('📥 download CSV', data=csv, file_name="candidate_ranking_top.csv", mime="text/csv")
            except Exception:
                pass


if __name__ == "__main__":
    main()


