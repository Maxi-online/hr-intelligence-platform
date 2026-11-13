"""
CandidateRanking - Streamlit Frontend

Минимальный UI под поток: вакансия → отклики → AI → ранжирование → ТОП.
"""

import os
import requests
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Optional

# Конфигурация страницы
st.set_page_config(
    page_title="CandidateRanking — ТОП откликнувшихся",
    page_icon="👑",
    layout="wide",
)

# Базовый URL gateway (в docker и локально)
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
                
                # Улучшенные сообщения об ошибках
                if resp.status_code == 401:
                    st.error("🔐 **Ошибка авторизации**: Необходимо настроить OAuth токены HH API в файле конфигурации.")
                elif resp.status_code == 403:
                    st.error("🚫 **Доступ запрещен**: Недостаточно прав. Убедитесь, что у вас есть права работодателя для просмотра откликов на вакансию.")
                elif resp.status_code == 404:
                    st.error("📭 **Не найдено**: Вакансия не существует или отклики недоступны.")
                elif resp.status_code == 429:
                    st.error("🚦 **Превышен лимит**: Слишком много запросов к HH API. Попробуйте позже.")
                else:
                    st.error(f"Ошибка API {resp.status_code}: {detail}")
                return None
            return resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Сетевая ошибка: {e}")
            return None


client = ApiClient(API_BASE_URL)


def format_experience_months(months: Optional[int]) -> str:
    if not months or months <= 0:
        return "—"
    years = months // 12
    rest = months % 12
    return f"{years} г. {rest} мес." if years else f"{months} мес."


def candidate_card(c: Dict[str, Any]) -> None:
    """Отображение карточки кандидата с полным мульти-агентным AI анализом"""
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            if c.get("photo_url"):
                st.image(c["photo_url"], width=100)
            else:
                st.image("https://via.placeholder.com/100x100?text=👤", width=100)
        with col2:
            title = c.get("title") or "Должность не указана"
            name = c.get("name") or "Кандидат"
            st.subheader(f"👤 {name}")
            st.write(f"**Должность:** {title}")

            # Ссылка на резюме и дата обновления
            link_col, upd_col, score_col = st.columns([1, 1, 1])
            with link_col:
                if c.get("url"):
                    st.link_button("📄 Резюме", c["url"])
            with upd_col:
                if c.get("updated_at"):
                    try:
                        upd = datetime.fromisoformat(c["updated_at"].replace("Z", "+00:00"))
                        st.caption(f"🕒 Обновлено: {upd.strftime('%d.%m.%Y')}")
                    except Exception:
                        pass
            with score_col:
                if c.get("score") is not None:
                    score = float(c.get("score") or 0)
                    color = "green" if score >= 80 else ("orange" if score >= 50 else "red")
                    st.markdown(f"**🤖 AI‑оценка:** :{color}[{score:.1f}%]")
            
            st.markdown("---")

            # Основная информация
            meta = []
            area_name = c.get("area", {}).get("name")
            if area_name:
                meta.append(f"🏙️ {area_name}")
            exp_months = (c.get("experience") or {}).get("total_months")
            if exp_months is not None:
                meta.append(f"🗓️ Опыт: {format_experience_months(exp_months)}")
            sal = c.get("salary") or {}
            if sal.get("from") or sal.get("to"):
                if sal.get("from") and sal.get("to"):
                    meta.append(f"💰 {sal['from']:,}–{sal['to']:,} {sal.get('currency','RUR')}")
                elif sal.get("from"):
                    meta.append(f"💰 от {sal['from']:,} {sal.get('currency','RUR')}")
                elif sal.get("to"):
                    meta.append(f"💰 до {sal['to']:,} {sal.get('currency','RUR')}")
            if meta:
                st.write(" · ".join(meta))

            # Навыки
            skills = c.get("skills") or []
            if skills:
                st.caption("**Навыки:** " + ", ".join(skills[:10]) + (" …" if len(skills) > 10 else ""))

            # Последнее место работы
            last_work = c.get("last_work")
            if last_work and last_work.get("position") and last_work.get("company"):
                st.write(f"**Последнее место работы:** {last_work['position']} в {last_work['company']}")

            # === МУЛЬТИ-АГЕНТНЫЙ AI АНАЛИЗ ===
            analysis_status = c.get("analysis_status")
            multi_agent_data = c.get("multi_agent_data")
            
            if c.get("score") and analysis_status == "completed" and multi_agent_data and isinstance(multi_agent_data, dict):
                st.markdown("---")
                st.subheader("🤖 Мульти-агентный AI анализ")
                
                # === МАСТЕР-ОТЧЕТ ===
                master_report = multi_agent_data.get("master_report", {})
                if master_report and isinstance(master_report, dict):
                    overall_score = master_report.get("overall_score", 0.0)
                    recommendation = master_report.get("recommendation", "Нет рекомендации")
                    
                    # Итоговая оценка и рекомендация
                    score_color = "green" if overall_score >= 80 else "orange" if overall_score >= 60 else "red"
                    st.markdown(f"### 🎯 **Итоговая оценка:** :{score_color}[{overall_score:.1f}%]")
                    st.success(f"**📋 Рекомендация:** {recommendation}")
                    
                    # === ОТЧЕТ МАСТЕР-КООРДИНАТОРА (ИНТЕРАКТИВНЫЙ) ===
                    master_assessment = master_report.get("master_assessment", "")
                    if master_assessment:
                        with st.expander("🧠 **Экспертное заключение AI координатора**", expanded=True):
                            st.markdown(master_assessment)
                    
                    # === ОЦЕНКИ АГЕНТОВ (ИНТЕРАКТИВНЫЕ) ===
                    individual_scores = master_report.get("individual_scores", {})
                    if individual_scores:
                        with st.expander("👥 **Краткие оценки всех агентов**", expanded=True):
                            # Создаем колонки для красивого отображения
                            for i, (agent_name, agent_score) in enumerate(individual_scores.items()):
                                if i % 2 == 0:  # Каждую вторую строку делаем в колонках
                                    cols = st.columns(2)
                                
                                col_idx = i % 2
                                with cols[col_idx]:
                                    agent_score_color = "green" if agent_score >= 80 else "orange" if agent_score >= 60 else "red"
                                    # Убираем кодировочные артефакты
                                    clean_agent_name = str(agent_name).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                    st.markdown(f"**{clean_agent_name}:** :{agent_score_color}[{agent_score:.1f}%]")
                    
                    # === ДЕТАЛЬНЫЕ ОТЧЕТЫ АГЕНТОВ (ИНТЕРАКТИВНЫЕ EXPANDER'Ы) ===
                    agent_reports = multi_agent_data.get("agent_reports", [])
                    if agent_reports and len(agent_reports) > 0:
                        st.markdown("---")
                        st.markdown("### 🔍 **ДЕТАЛЬНЫЕ ОТЧЕТЫ АГЕНТОВ**")
                        
                        # Интерактивные expander'ы для каждого агента
                        for i, report in enumerate(agent_reports):
                            if not isinstance(report, dict):
                                continue
                                
                            agent_name = report.get("agent_name", f"Агент {i+1}")
                            agent_score = report.get("score", 0)
                            status = report.get("status", "unknown")
                            summary = report.get("summary", "Нет описания")
                            
                            # Убираем кодировочные артефакты
                            clean_agent_name = str(agent_name).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                            clean_summary = str(summary).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                            
                            # Определяем цвет и эмодзи статуса
                            status_mapping = {
                                "pass": ("green", "✅"),
                                "warning": ("orange", "⚠️"),
                                "fail": ("red", "❌"),
                                "error": ("red", "🔥")
                            }
                            status_color, status_emoji = status_mapping.get(status, ("gray", "❓"))
                            
                            # ИНТЕРАКТИВНЫЙ EXPANDER ДЛЯ КАЖДОГО АГЕНТА
                            with st.expander(
                                f"{status_emoji} **{clean_agent_name}** — {agent_score:.1f}% — _{clean_summary}_",
                                expanded=False  # По умолчанию свернуты
                            ):
                                # Детальная информация от агента
                                details = report.get("details", [])
                                red_flags = report.get("red_flags", [])
                                positive_points = report.get("positive_points", [])
                                recommendations = report.get("recommendations", [])
                                
                                if details:
                                    st.markdown("**🔍 Детальный анализ:**")
                                    for detail in details:
                                        clean_detail = str(detail).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        st.markdown(f"• {clean_detail}")
                                
                                if red_flags:
                                    st.markdown("**🚩 Выявленные проблемы:**")
                                    for flag in red_flags:
                                        clean_flag = str(flag).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        st.error(f"• {clean_flag}")
                                
                                if positive_points:
                                    st.markdown("**✅ Сильные стороны:**")
                                    for point in positive_points:
                                        clean_point = str(point).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        st.success(f"• {clean_point}")
                                
                                if recommendations:
                                    st.markdown("**💡 Рекомендации:**")
                                    for rec in recommendations:
                                        clean_rec = str(rec).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        st.info(f"• {clean_rec}")
                    
                    # === БОНУС ЗА РЕЛЕВАНТНОСТЬ ===
                    relevance_boost = c.get("relevance_boost", 0)
                    if relevance_boost and relevance_boost > 0:
                        st.info(f"🎯 **Бонус за релевантность поиска:** +{relevance_boost:.1f}%")
                    
                    # === ФОРМУЛА РАСЧЕТА (ИНТЕРАКТИВНАЯ) ===
                    active_agents = multi_agent_data.get("active_agents", [])
                    total_time = multi_agent_data.get("total_processing_time", 0)
                    
                    with st.expander("🔢 **Формула расчета и технические детали**", expanded=False):
                        formula_text = f"""
🧮 ФОРМУЛА РАСЧЕТА:
Итоговая оценка = Среднее арифметическое({len(active_agents)} агентов) + Бонус релевантности

🤖 АКТИВНЫЕ АГЕНТЫ ({len(active_agents)}):
• Анализ требований позиции
• Технические навыки и опыт  
• Уровень владения навыками
• Качество резюме как документа
• Профессиональный опыт
• Оформление и структура
• Детекция аномалий и несоответствий

⚡ Время обработки: {total_time:.3f}с
                        """
                        st.code(formula_text, language="text")
            
            # FALLBACK: если мульти-агентных данных нет
            elif c.get("score"):
                st.markdown("---")
                st.subheader("🤖 AI анализ")
                
                if analysis_status != "completed":
                    st.warning("⚠️ Мульти-агентный анализ не завершен или недоступен")
                
                # Краткое резюме анализа
                analysis_summary = c.get("analysis_summary")
                if analysis_summary and analysis_summary != "Краткий анализ недоступен":
                    st.info(f"**📝 Резюме анализа:** {analysis_summary}")
                
                # Обоснование AI
                reasoning = c.get("reasoning")
                if reasoning:
                    st.subheader("🧠 Обоснование AI")
                    st.write(reasoning)

        st.markdown("---")


def main():
    st.title("👑 CandidateRanking — ТОП откликнувшихся по вакансии")
    st.markdown("Вставьте ссылку на вакансию hh.ru. Сервис загрузит отклики, выполнит AI‑анализ и построит ТОП.")
    
    # Показываем информацию о настройке
    with st.expander("ℹ️ Настройка системы", expanded=False):
        st.markdown("""
        **Для работы системы необходимо:**
        1. **OAuth токены HH API** — для доступа к откликам на ваши вакансии
        2. **OpenAI API ключ** — для AI-анализа резюме кандидатов
        
        **Настройка:**
        - Скопируйте `config/settings.yaml.template` в `config/settings.yaml`
        - Заполните поля `hh_api.client_id`, `hh_api.client_secret`, `hh_api.user_tokens.access_token`
        - Добавьте OpenAI ключ в `ai_analysis.openai_api_key`
        
        **Важно:** Система работает только с вакансиями, которые принадлежат вашему работодательскому аккаунту на hh.ru
        """)

    health = client.request("GET", "/health")
    if not health:
        st.error("Gateway недоступен. Убедитесь, что система запущена (docker-compose up -d --build).")
        st.stop()

    with st.form("vacancy_form"):
        vacancy_url = st.text_input("Ссылка на вакансию", placeholder="https://hh.ru/vacancy/123456789")
        limit = st.slider("Сколько кандидатов показать в ТОПе", 3, 50, 10, 1)
        submitted = st.form_submit_button("Построить ТОП по откликам")

    if submitted:
        if not vacancy_url.strip():
            st.error("Укажите ссылку на вакансию")
            st.stop()

        with st.spinner("Загружаем отклики, анализируем, строим ТОП…"):
            payload = {"vacancy_url": vacancy_url.strip(), "limit": int(limit)}
            resp = client.request("POST", "/vacancy/top", json=payload)
            if not resp:
                st.error("Не удалось получить ТОП по вакансии")
                st.stop()

        vacancy_id = resp.get("vacancy_id", "")
        total_responses = resp.get("total_responses", 0)
        candidates = resp.get("candidates", [])

        st.subheader(f"ТОП кандидатов (вакансия {vacancy_id})")
        if not candidates:
            if total_responses == 0:
                st.info("📭 **По этой вакансии пока нет откликов** или у вас нет доступа к ним.")
                st.markdown("""
                **Возможные причины:**
                - Вакансия принадлежит не вашему работодательскому аккаунту  
                - OAuth токены настроены неправильно
                - Вакансия неактивна или снята с публикации
                - Действительно пока нет откликов
                """)
            else:
                st.warning("⚠️ Не удалось обработать отклики. Попробуйте позже.")
        else:
            # Отображение кандидатов
            for i, cand in enumerate(candidates, 1):
                score = cand.get("score", 0) or 0
                name = cand.get("name", "Кандидат")
                title = cand.get("title", "Должность не указана")
                score_color = "🟢" if score >= 80 else ("🟡" if score >= 50 else "🔴")
                
                st.markdown(f"### #{i} {score_color} **{name}** — {title} (AI: {score:.1f}%)")
                candidate_card(cand)
                st.markdown("---")

            # Таблица и экспорт
            try:
                import pandas as pd
                df = pd.DataFrame(candidates)
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 Скачать CSV", data=csv, file_name="candidate_ranking_top.csv", mime="text/csv")
            except Exception:
                pass


if __name__ == "__main__":
    main()


