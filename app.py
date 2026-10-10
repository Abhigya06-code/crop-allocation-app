"""
Crop Allocation Advisor.
SETUP (once): pip install streamlit psycopg2-binary pandas matplotlib fpdf2 pillow uharfbuzz
RUN: streamlit run app.py
"""

import html
import streamlit as st
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

DARK = "#14261A"
DARK2 = "#1F3A26"
PRIMARY = "#2C5F2D"
SECOND = "#8FB57A"
ACCENT = "#D69A52"
PAGE_BG = "#F3F6EF"
TEXT_ON_DARK = "#EAF0E6"

st.set_page_config(page_title="Crop Allocation Advisor", page_icon=None, layout="wide")

st.markdown(f"""<style>
  .stApp {{ background: {PAGE_BG}; }}
  .block-container {{ padding-top: 0; max-width: 1180px; }}
  h1,h2,h3,h4 {{ font-family: Georgia, serif; }}

  .header-band {{ background: {DARK}; padding: 2.4rem 2.2rem 2rem 2.2rem; margin: 0 -5rem 1.8rem -5rem; }}
  .header-band h1 {{ color: white !important; margin: 0; font-size: 2.1rem; font-weight: 700; }}
  .header-band p {{ color: {SECOND} !important; margin: 0.35rem 0 0 0; font-size: 0.85rem; letter-spacing: 1px; text-transform: uppercase; }}

  /* Section labels always sit on the light page background */
  .section-label {{ color: {DARK} !important; font-weight: 700; font-size: 1.15rem; font-family: Georgia, serif; display: block; margin: 1.2rem 0 0.7rem 0; }}

  /* Force every input widget to a readable light style, regardless of Streamlit theme */
  .stTextInput input, .stNumberInput input {{
    background-color: white !important; color: {DARK} !important;
    border: 1px solid #C9D6BC !important; border-radius: 6px !important;
  }}
  div[data-baseweb="select"] > div {{
    background-color: white !important; color: {DARK} !important;
    border: 1px solid #C9D6BC !important; border-radius: 6px !important;
  }}
  div[data-baseweb="select"] span, div[data-baseweb="select"] div {{ color: {DARK} !important; }}
  .stTextInput label, .stNumberInput label, .stSelectbox label {{ color: {DARK} !important; font-weight: 600; }}
  ::placeholder {{ color: #8A9A80 !important; opacity: 1; }}

  [data-testid="stForm"] {{ background: white; border: 1px solid #DCE6D2; border-radius: 12px; padding: 1.8rem 2rem; box-shadow: 0 2px 10px rgba(20,38,26,0.06); }}

  div[data-testid="stMetric"] {{ background: white; border: 1px solid #DCE6D2; border-radius: 8px; padding: 0.9rem; }}
  div[data-testid="stMetricValue"] {{ color: {PRIMARY} !important; }}
  div[data-testid="stMetricLabel"] {{ color: {DARK} !important; }}

  .metric-card {{ background: white; border: 1px solid #DCE6D2; border-radius: 8px; padding: 0.9rem 1rem; transition: box-shadow 0.15s ease; }}
  .metric-card:hover {{ box-shadow: 0 4px 14px rgba(20,38,26,0.10); }}
  .metric-card .metric-label {{ color: {DARK} !important; font-size: 0.82rem; font-weight: 600; opacity: 0.85; }}
  .metric-card .metric-value {{ color: {PRIMARY} !important; font-size: 1.5rem; font-weight: 700; font-family: Georgia, serif; margin-top: 0.15rem; }}

  .stButton>button, .stDownloadButton>button {{ background: {ACCENT}; color: white !important; border-radius: 6px; border: none; font-weight: 600; padding: 0.6rem; }}
  .stButton>button:hover, .stDownloadButton>button:hover {{ background: #B87F3A; color: white !important; }}

  .why-card {{ background: white; border: 1px solid #DCE6D2; border-left: 4px solid {PRIMARY}; padding: 0.8rem 1.1rem; border-radius: 6px; margin-bottom: 0.5rem; color: {DARK} !important; }}
  .why-card b {{ color: {DARK} !important; }}
  .why-card .sub {{ color: #5B6E56 !important; font-size: 0.9rem; }}

  .sql-box {{ background: #14261A; color: #9CDCFE; font-family: Consolas, monospace; font-size: 0.82rem; padding: 0.9rem 1.1rem; border-radius: 8px; white-space: pre-wrap; margin-bottom: 0.4rem; }}
  .stage-label {{ color: {DARK} !important; font-weight: 700; font-size: 1rem; font-family: Georgia, serif; }}
  .stage-desc {{ color: #5B6E56 !important; font-size: 0.88rem; margin-bottom: 0.5rem; }}

  [data-testid="stExpander"] {{ border: 1px solid {ACCENT} !important; border-radius: 8px !important; background: #FFF8EF !important; }}
  [data-testid="stExpander"] summary {{ background: {ACCENT} !important; border-radius: 7px 7px 0 0 !important; }}
  [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span, [data-testid="stExpander"] summary svg {{ color: white !important; font-weight: 700 !important; fill: white !important; }}

  .hero {{ background: linear-gradient(135deg, {PRIMARY}, {DARK2}); border-radius: 14px; padding: 1.8rem 2.2rem; margin: 1.2rem 0 1.6rem 0; box-shadow: 0 6px 18px rgba(20,38,26,0.18); }}
  .hero .label {{ color: {SECOND}; text-transform: uppercase; letter-spacing: 1.5px; font-size: 0.78rem; font-weight: 700; }}
  .hero .crop {{ color: white; font-family: Georgia, serif; font-size: 2.1rem; font-weight: 700; margin: 0.2rem 0; }}
  .hero .detail {{ color: {TEXT_ON_DARK}; font-size: 0.95rem; }}

  /* Numbered step badge used in the live-SQL pipeline walkthrough */
  .step-row {{ display: flex; align-items: center; gap: 0.6rem; margin-top: 1.1rem; }}
  .step-badge {{ flex: 0 0 auto; width: 28px; height: 28px; border-radius: 50%; background: {PRIMARY};
    color: white !important; font-weight: 700; font-size: 0.9rem; display: flex; align-items: center;
    justify-content: center; font-family: Georgia, serif; }}
  .step-status {{ margin-left: auto; color: {PRIMARY} !important; font-size: 0.78rem; font-weight: 700;
    background: #E7F1DF; padding: 0.15rem 0.6rem; border-radius: 999px; white-space: nowrap; }}
  .row-count {{ color: #5B6E56 !important; font-size: 0.78rem; font-style: italic; margin: 0.15rem 0 0.5rem 0; }}

  /* Compact strip showing all pipeline stages at a glance */
  .pipeline-strip {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.6rem 0 1rem 0; }}
  .pipeline-chip {{ background: white; border: 1px solid #DCE6D2; border-left: 4px solid {PRIMARY};
    border-radius: 6px; padding: 0.4rem 0.8rem; font-size: 0.78rem; color: {DARK} !important; font-weight: 600; }}

  footer {{visibility: hidden;}}
</style>""", unsafe_allow_html=True)

T = {
    "en": {
        "title": "Crop Allocation Advisor", "subtitle": "Database-Driven Land Allocation · Tamil Nadu",
        "db": "Database", "pw": "Postgres password",
        "pipeline": "Pipeline", "pipeline_desc": "Soil/season filter, price forecast, water/budget limits, blended scoring, land split, audit log",
        "enter_pw": "Enter your Postgres password in the sidebar to get started.",
        "form_title": "Enter your plot details", "name": "Your name",
        "district": "District (select from Tamil Nadu's 37 districts)", "season": "Season",
        "land": "Land available — in acres", "budget": "Budget — in rupees (₹)",
        "water": "Water available — in mm per acre",
        "land_ph": "e.g. 2", "budget_ph": "e.g. 40000", "water_ph": "e.g. 1000",
        "submit": "Get my crop plan", "missing": "Please fill in every field before submitting.",
        "plan_for": "Plan for", "land_m": "Land (acres)", "budget_m": "Budget (₹)", "rec_m": "Crops recommended",
        "avg_profit": "Avg. profit per acre (₹)", "your_plan": "Your Crop Plan", "not_rec": "Not Recommended",
        "allocation": "Land Allocation", "details": "Details", "download_pdf": "Download plan as PDF",
        "download_csv": "Download as CSV", "why_chosen": "Why each crop was chosen",
        "no_crops": "No crops were profitable and within limits for this plot. Try a larger budget or more water.",
        "all_included": "Every eligible crop made it into the plan, nothing was excluded.",
        "top_pick": "Top Recommendation", "top_pick_of": "of your land",
        "footer": "Crop Allocation Advisor · DBMS Course Project · Batch 6",
        "behind_scenes": "See How This Was Calculated (Live SQL)",
        "stage1_title": "Soil Eligibility Filter",
        "stage1_desc": "Which crops can even grow in this district's soil, based on pH range.",
        "stage2_title": "Price Forecast",
        "stage2_desc": "The forecasted price already sitting in the database for this district, from the trained model.",
        "stage2_desc_ci": "The forecasted price for this district from the trained model, with its 95% likely range. The score uses a risk-adjusted price inside that range, so a shaky forecast counts for less.",
        "stage3_title": "Budget, Water & Rainfall Constraints",
        "stage3_desc": "Checking each crop's real cost (after the bulk-purchase discount for larger farms), water need and seasonal rainfall against what the farmer actually has.",
        "stage4_title": "Blended Scoring & Land Split",
        "stage4_desc": "The final blended score for each eligible crop, and how the land was split between them.",
        "stage5_title": "Audit Log",
        "stage5_desc": "Every crop the system considered, included or not, with the exact reason recorded for the decision.",
        "run_query": "Live query result:", "rows_returned": "row(s) returned",
        "pipeline_overview": "5-step live pipeline", "step_done": "Executed live",
        "pdf_title": "Crop Allocation Plan", "pdf_land": "Land", "pdf_budget": "Budget", "pdf_water": "Water",
        "pdf_top": "TOP RECOMMENDATION", "pdf_of_land": "of your land",
        "pdf_recommended": "Recommended Crops", "pdf_crop": "Crop", "pdf_land_pct": "Land %", "pdf_season": "Season",
        "pdf_note": "Sowing dates omitted here for space; see the full breakdown below.",
        "pdf_sowing": "Sowing Windows", "pdf_sow_from": "Sow From", "pdf_sow_to": "Sow To",
        "pdf_why": "Why each crop was chosen", "pdf_not_rec": "Not Recommended",
        "pdf_footer": "Crop Allocation Advisor - DBMS Course Project - Batch 6",
        "pdf_tamil_note": "Note: this PDF is shown in English because the Tamil font or the text-shaping package (uharfbuzz) isn't available on the server; the on-screen plan above is fully in Tamil.",
        "sidebar_tip": "After you submit, scroll to the bottom: the \"{panel}\" panel is open by default and shows all 5 pipeline steps with the actual live SQL.",
        "invalid_name": "Please enter your name.",
        "land_big": "That is an unusually large plot (over 500 acres). Please check the figure; the plan below uses it as entered.",
        "db_down": "The database could not be reached. Check that PostgreSQL is running and that the password is correct.",
        "fn_missing": "The allocation function (run_allocation) is missing from this database. Install it first, then try again.",
        "fc_label": "Forecast price", "fc_range": "likely range", "fc_unit": "per quintal",
        "nav_label": "View", "nav_plan": "Get a Crop Plan", "nav_dashboard": "District Dashboard",
        "dash_title": "District & Crop Dashboard",
        "dash_subtitle": "Aggregated patterns across every plan generated so far — not just the current farmer.",
        "dash_no_data": "No farmer requests yet. Generate at least one crop plan first, then come back here.",
        "dash_total_requests": "Total requests", "dash_total_farmers": "Farmers served",
        "dash_districts": "Districts represented", "dash_top_crop_overall": "Most-recommended crop overall",
        "dash_inclusion_title": "How Often Each Crop Is Included",
        "dash_inclusion_desc": "Across every plan generated so far, counting how many times each crop was included.",
        "dash_share_title": "Average Land Share When Included",
        "dash_share_desc": "For crops that were included at least once, their average share of the land they were given.",
        "dash_district_title": "Top Crop by District",
        "dash_district_desc": "The single most-recommended crop in each district with at least one request, found with a SQL window function (RANK) over crop-inclusion counts grouped by district.",
        "dash_col_district": "District", "dash_col_top_crop": "Top Crop", "dash_col_times": "Times Recommended",
        "dash_exclusion_title": "Why Crops Get Excluded",
        "dash_exclusion_desc": "Every excluded crop, across every request so far, grouped by the reason it was excluded.",
        "dash_reason_budget": "Budget", "dash_reason_water": "Water", "dash_reason_rainfall": "Rainfall",
        "dash_reason_price": "No price data", "dash_reason_score": "Unprofitable", "dash_reason_other": "Other",
        "dash_sql_title": "See the Dashboard's Live SQL",
        "dash_sql_desc": "Every chart and table above comes straight from these four queries, run live, not a cached summary.",
    },
    "ta": {
        "title": "பயிர் ஒதுக்கீடு ஆலோசகர்", "subtitle": "தரவுத்தள அடிப்படையிலான நில ஒதுக்கீடு · தமிழ்நாடு",
        "db": "தரவுத்தளம்", "pw": "Postgres கடவுச்சொல்",
        "pipeline": "செயல்முறை", "pipeline_desc": "மண்/பருவ வடிகட்டி, விலை முன்னறிவிப்பு, நீர்/பட்ஜெட் வரம்பு, மதிப்பீடு, நில பிரிவு, காரணப் பதிவு",
        "enter_pw": "தொடங்க பக்கப்பட்டியில் உங்கள் Postgres கடவுச்சொல்லை உள்ளிடவும்.",
        "form_title": "உங்கள் நிலத்தின் விவரங்களை உள்ளிடவும்", "name": "உங்கள் பெயர்",
        "district": "மாவட்டம் (37 மாவட்டங்களிலிருந்து தேர்ந்தெடுக்கவும்)", "season": "பருவம்",
        "land": "கிடைக்கும் நிலம் — ஏக்கரில்", "budget": "பட்ஜெட் — ரூபாயில் (₹)",
        "water": "கிடைக்கும் நீர் — மிமீ/ஏக்கர்",
        "land_ph": "எ.கா. 2", "budget_ph": "எ.கா. 40000", "water_ph": "எ.கா. 1000",
        "submit": "எனது பயிர் திட்டத்தைப் பெறு", "missing": "சமர்ப்பிக்கும் முன் அனைத்து புலங்களையும் நிரப்பவும்.",
        "plan_for": "திட்டம்", "land_m": "நிலம் (ஏக்கர்)", "budget_m": "பட்ஜெட் (₹)", "rec_m": "பரிந்துரைக்கப்பட்ட பயிர்கள்",
        "avg_profit": "சராசரி லாபம்/ஏக்கர் (₹)", "your_plan": "உங்கள் பயிர் திட்டம்", "not_rec": "பரிந்துரைக்கப்படவில்லை",
        "allocation": "நில ஒதுக்கீடு", "details": "விவரங்கள்", "download_pdf": "PDF பதிவிறக்கு",
        "download_csv": "CSV பதிவிறக்கு", "why_chosen": "ஒவ்வொரு பயிரும் ஏன் தேர்ந்தெடுக்கப்பட்டது",
        "no_crops": "இந்த நிலத்திற்கு லாபகரமான பயிர்கள் இல்லை. அதிக பட்ஜெட் அல்லது நீரை முயற்சிக்கவும்.",
        "all_included": "தகுதியான அனைத்து பயிர்களும் திட்டத்தில் சேர்க்கப்பட்டன.",
        "top_pick": "சிறந்த பரிந்துரை", "top_pick_of": "உங்கள் நிலத்தில்",
        "footer": "பயிர் ஒதுக்கீடு ஆலோசகர் · DBMS பாடத்திட்டம் · Batch 6",
        "behind_scenes": "இது எப்படி கணக்கிடப்பட்டது (நேரடி SQL)",
        "stage1_title": "மண் தகுதி வடிகட்டி",
        "stage1_desc": "இந்த மாவட்டத்தின் மண் pH அடிப்படையில் எந்த பயிர்கள் வளரக்கூடும்.",
        "stage2_title": "விலை முன்னறிவிப்பு",
        "stage2_desc": "பயிற்சி பெற்ற மாதிரியிலிருந்து இந்த மாவட்டத்திற்கான முன்னறிவிக்கப்பட்ட விலை.",
        "stage2_desc_ci": "பயிற்சி பெற்ற மாதிரியிலிருந்து இந்த மாவட்டத்திற்கான முன்னறிவிக்கப்பட்ட விலை மற்றும் அதன் 95% சாத்தியமான வரம்பு. மதிப்பெண் இந்த வரம்பிற்குள் இடர்-சரிசெய்த விலையைப் பயன்படுத்துகிறது; எனவே நிச்சயமற்ற முன்னறிவிப்பிற்கு குறைவான மதிப்பு.",
        "stage3_title": "பட்ஜெட், நீர் மற்றும் மழை வரம்புகள்",
        "stage3_desc": "ஒவ்வொரு பயிரின் உண்மையான செலவு (பெரிய நிலங்களுக்கான மொத்த கொள்முதல் தள்ளுபடிக்குப் பின்), நீர் தேவை மற்றும் பருவ மழையை விவசாயியிடம் உள்ளதோடு சரிபார்த்தல்.",
        "stage4_title": "கலப்பு மதிப்பெண் & நில பிரிவு",
        "stage4_desc": "தகுதியான ஒவ்வொரு பயிருக்கான இறுதி மதிப்பெண் மற்றும் நிலம் எவ்வாறு பிரிக்கப்பட்டது.",
        "stage5_title": "காரணப் பதிவு",
        "stage5_desc": "கருதப்பட்ட ஒவ்வொரு பயிரும் (சேர்க்கப்பட்டதா இல்லையா), அதற்கான துல்லியமான காரணத்துடன்.",
        "run_query": "நேரடி வினவல் முடிவு:", "rows_returned": "வரிசைகள் கிடைத்தன",
        "pipeline_overview": "5-படி நேரடி செயல்முறை", "step_done": "நேரடியாக இயக்கப்பட்டது",
        "pdf_title": "பயிர் ஒதுக்கீடு திட்டம்", "pdf_land": "நிலம்", "pdf_budget": "பட்ஜெட்", "pdf_water": "நீர்",
        "pdf_top": "சிறந்த பரிந்துரை", "pdf_of_land": "உங்கள் நிலத்தில்",
        "pdf_recommended": "பரிந்துரைக்கப்பட்ட பயிர்கள்", "pdf_crop": "பயிர்", "pdf_land_pct": "நிலம் %", "pdf_season": "பருவம்",
        "pdf_note": "விதைப்பு தேதிகள் இங்கு தவிர்க்கப்பட்டுள்ளன; கீழே முழு விவரம் காண்க.",
        "pdf_sowing": "விதைப்பு காலம்", "pdf_sow_from": "தொடக்கம்", "pdf_sow_to": "முடிவு",
        "pdf_why": "ஒவ்வொரு பயிரும் ஏன் தேர்ந்தெடுக்கப்பட்டது", "pdf_not_rec": "பரிந்துரைக்கப்படவில்லை",
        "pdf_footer": "பயிர் ஒதுக்கீடு ஆலோசகர் - DBMS பாடத்திட்டம் - Batch 6",
        "pdf_tamil_note": "குறிப்பு: சேவையகத்தில் தமிழ் எழுத்துரு அல்லது உரை வடிவமைப்புத் தொகுப்பு (uharfbuzz) இல்லாததால் இந்த PDF ஆங்கிலத்தில் உள்ளது; மேலே உள்ள திரைத் திட்டம் முழுவதும் தமிழில் உள்ளது.",
        "sidebar_tip": "சமர்ப்பித்த பிறகு கீழே செல்லவும்: \"{panel}\" பகுதி தானாகவே திறந்திருக்கும்; 5 படிகளையும் நேரடி SQL உடன் காட்டும்.",
        "invalid_name": "உங்கள் பெயரை உள்ளிடவும்.",
        "land_big": "இது மிகப் பெரிய நிலம் (500 ஏக்கருக்கு மேல்). எண்ணைச் சரிபார்க்கவும்; கீழுள்ள திட்டம் நீங்கள் உள்ளிட்டதையே பயன்படுத்துகிறது.",
        "db_down": "தரவுத்தளத்துடன் இணைக்க முடியவில்லை. PostgreSQL இயங்குகிறதா, கடவுச்சொல் சரியா என்று சரிபார்க்கவும்.",
        "fn_missing": "இந்த தரவுத்தளத்தில் ஒதுக்கீட்டு செயல்பாடு (run_allocation) இல்லை. முதலில் அதை நிறுவி, மீண்டும் முயற்சிக்கவும்.",
        "fc_label": "முன்னறிவிப்பு விலை", "fc_range": "சாத்தியமான வரம்பு", "fc_unit": "குவிண்டாலுக்கு",
        "nav_label": "காட்சி", "nav_plan": "பயிர் திட்டம் பெறு", "nav_dashboard": "மாவட்ட டாஷ்போர்டு",
        "dash_title": "மாவட்டம் & பயிர் டாஷ்போர்டு",
        "dash_subtitle": "இதுவரை உருவாக்கப்பட்ட அனைத்து திட்டங்களிலும் உள்ள மொத்த போக்குகள் — தற்போதைய விவசாயி மட்டும் அல்ல.",
        "dash_no_data": "இன்னும் கோரிக்கைகள் இல்லை. முதலில் ஒரு பயிர் திட்டத்தை உருவாக்கி, பின் இங்கு திரும்பி வரவும்.",
        "dash_total_requests": "மொத்த கோரிக்கைகள்", "dash_total_farmers": "சேவை செய்யப்பட்ட விவசாயிகள்",
        "dash_districts": "பிரதிநிதித்துவப்படுத்தப்பட்ட மாவட்டங்கள்", "dash_top_crop_overall": "அதிகம் பரிந்துரைக்கப்பட்ட பயிர்",
        "dash_inclusion_title": "ஒவ்வொரு பயிரும் எத்தனை முறை சேர்க்கப்பட்டது",
        "dash_inclusion_desc": "இதுவரை உருவாக்கப்பட்ட அனைத்து திட்டங்களிலும், ஒவ்வொரு பயிரும் எத்தனை முறை சேர்க்கப்பட்டது என்பதன் எண்ணிக்கை.",
        "dash_share_title": "சேர்க்கப்படும்போது சராசரி நில பங்கு",
        "dash_share_desc": "குறைந்தது ஒரு முறையாவது சேர்க்கப்பட்ட பயிர்களுக்கு, அவை பெற்ற நிலத்தின் சராசரி பங்கு.",
        "dash_district_title": "மாவட்டம் வாரியாக சிறந்த பயிர்",
        "dash_district_desc": "குறைந்தது ஒரு கோரிக்கையாவது உள்ள ஒவ்வொரு மாவட்டத்திலும் அதிகம் பரிந்துரைக்கப்பட்ட பயிர், மாவட்டம் வாரியாக குழுவாக்கப்பட்ட பயிர்-சேர்க்கை எண்ணிக்கைகள் மீது SQL சாளர செயல்பாடு (RANK) மூலம் கண்டறியப்பட்டது.",
        "dash_col_district": "மாவட்டம்", "dash_col_top_crop": "சிறந்த பயிர்", "dash_col_times": "பரிந்துரைக்கப்பட்ட முறை",
        "dash_exclusion_title": "பயிர்கள் ஏன் விலக்கப்படுகின்றன",
        "dash_exclusion_desc": "இதுவரை உள்ள ஒவ்வொரு கோரிக்கையிலும் விலக்கப்பட்ட ஒவ்வொரு பயிரும், விலக்கப்பட்ட காரணத்தின் அடிப்படையில் குழுவாக்கப்பட்டது.",
        "dash_reason_budget": "பட்ஜெட்", "dash_reason_water": "நீர்", "dash_reason_rainfall": "மழைப்பொழிவு",
        "dash_reason_price": "விலை தரவு இல்லை", "dash_reason_score": "லாபகரமற்றது", "dash_reason_other": "மற்றவை",
        "dash_sql_title": "டாஷ்போர்டின் நேரடி SQL ஐப் பார்க்கவும்",
        "dash_sql_desc": "மேலே உள்ள ஒவ்வொரு விளக்கப்படமும் அட்டவணையும் இந்த நான்கு வினவல்களிலிருந்து நேரடியாக வருகின்றன, சேமிக்கப்பட்ட சுருக்கம் அல்ல.",
    },
}

CROP_TA = {"Groundnut": "நிலக்கடலை", "Maize": "சோளம்", "Brinjal": "கத்திரிக்காய்", "Tomato": "தக்காளி",
           "Onion": "வெங்காயம்", "Green Chilli": "பச்சை மிளகாய்", "Rice (Paddy)": "நெல்", "Sugarcane": "கரும்பு"}

def crop_label(name, lang):
    return name + (f" ({CROP_TA[name]})" if lang == "ta" and name in CROP_TA else "")

def clean_reason(reason):
    """Strip the specific rupee profit/loss figure and replace it with a
    plain ranking statement. The number is a rough gross-margin estimate
    (no labor, transport, commission, or market-saturation effects), so
    we show WHY a crop ranked where it did without quoting it as a
    guaranteed amount."""
    if not reason:
        return ""
    if "estimated profit of Rs." in reason:
        return "Included: ranks well among eligible crops based on recent market prices and the price forecast."
    if "estimated loss of Rs." in reason:
        return "Excluded: ranks poorly among eligible crops based on recent market prices and the price forecast."
    return reason

def build_pdf(name, district, land_acres, budget_inr, water_available, df, excluded_rows, lang="en"):
    import io, os

    L = T[lang]

    pdf = FPDF(format="A4")
    pdf.add_page()
    page_w = pdf.w

    # fpdf2's core fonts (Helvetica etc.) only cover Latin script, so raw
    # Tamil text would render as blank boxes. If a Tamil-capable TTF is
    # available on the server we use it and the PDF comes out fully in
    # Tamil; if not, we fall back to English for the PDF only (the
    # on-screen plan stays in Tamil either way) and note that at the
    # bottom of the PDF instead of silently mismatching the app.
    # Tamil needs a Tamil-capable TTF AND complex-text shaping (uharfbuzz):
    # without shaping, vowel signs are drawn in the wrong place and the
    # words come out subtly misspelled even though every glyph is present.
    # So we only produce a Tamil PDF when both are available; otherwise we
    # fall back to English and say so at the bottom of the PDF.
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    tamil_font_paths = [  # (regular, bold or None)
        (os.path.join(font_dir, "NotoSansTamil-Regular.ttf"), os.path.join(font_dir, "NotoSansTamil-Bold.ttf")),
        ("/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf"),
        ("/usr/share/fonts/opentype/noto/NotoSansTamil-Regular.otf", "/usr/share/fonts/opentype/noto/NotoSansTamil-Bold.otf"),
        ("/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf", None),
    ]
    tamil_font_ready = False
    tamil_bold_ready = False
    if lang == "ta":
        try:
            import uharfbuzz  # noqa: F401
            shaping_ok = True
        except Exception:
            shaping_ok = False
        if shaping_ok:
            for reg, bold in tamil_font_paths:
                if reg and os.path.exists(reg):
                    try:
                        pdf.add_font("NotoTamil", "", reg)
                        tamil_font_ready = True
                        if bold and os.path.exists(bold):
                            pdf.add_font("NotoTamil", "B", bold)
                            tamil_bold_ready = True
                        pdf.set_text_shaping(True)
                        break
                    except Exception:
                        tamil_font_ready = False
    use_ta = lang == "ta" and tamil_font_ready
    L_pdf = L if use_ta else T["en"]
    base_font = "NotoTamil" if use_ta else "Helvetica"

    def set_pdf_font(style="", size=10):
        # Tamil: use the real bold face when it was found, regular
        # otherwise; there is no italic face, so italic maps to regular.
        if base_font == "NotoTamil":
            pdf.set_font(base_font, "B" if ("B" in style and tamil_bold_ready) else "", size)
        else:
            pdf.set_font(base_font, style, size)

    def crop_disp(nm):
        return crop_label(nm, lang) if use_ta else nm

    # ---- Dark green header band ----
    pdf.set_fill_color(20, 38, 26)
    pdf.rect(0, 0, page_w, 32, "F")
    pdf.set_xy(10, 8)
    set_pdf_font("B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, L_pdf["pdf_title"], ln=True)
    pdf.set_x(10)
    set_pdf_font("", 10.5)
    pdf.set_text_color(143, 181, 122)
    pdf.cell(0, 6, f"{name}  -  {district} district", ln=True)
    pdf.set_x(10)
    pdf.cell(0, 6, f"{L_pdf['pdf_land']}: {land_acres} acres   |   {L_pdf['pdf_budget']}: Rs. {budget_inr:,}   |   {L_pdf['pdf_water']}: {water_available} mm/acre", ln=True)
    pdf.set_y(38)

    # ---- Top recommendation highlight ----
    top = df.iloc[0]
    pdf.set_fill_color(44, 95, 45)
    pdf.rect(10, pdf.get_y(), page_w - 20, 20, "F")
    pdf.set_xy(14, pdf.get_y() + 3)
    set_pdf_font("", 8.5)
    pdf.set_text_color(143, 181, 122)
    pdf.cell(0, 5, L_pdf["pdf_top"], ln=True)
    pdf.set_x(14)
    set_pdf_font("B", 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, f"{crop_disp(top['Crop'])}  -  {top['Land share (%)']}% {L_pdf['pdf_of_land']}", ln=True)
    pdf.ln(8)

    # ---- Pie chart, same colors as the app ----
    fig, ax = plt.subplots(figsize=(3.6, 3.6))
    palette = ["#2C5F2D", "#6E9B4F", "#97BC62", "#D69A52", "#B4CB8F", "#4A7A3D"]
    colors = [palette[i % len(palette)] for i in range(len(df))]
    wedges, texts, autotexts = ax.pie(
        df["Land share (%)"], labels=df["Crop"], autopct="%1.1f%%",
        colors=colors, startangle=90, textprops={"fontsize": 8.5, "color": "#14261A"},
        wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    for at in autotexts:
        at.set_color("white"); at.set_fontweight("bold"); at.set_fontsize(8)
    ax.axis("equal")
    fig.patch.set_facecolor("white")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)

    chart_y = pdf.get_y()
    chart_display_w = 75
    # Measure the chart's real rendered dimensions instead of guessing,
    # since bbox_inches='tight' crops the figure differently depending
    # on how many crops (and how long their labels) are in the chart.
    from PIL import Image as _PILImage
    buf.seek(0)
    _img = _PILImage.open(buf)
    _img_w_px, _img_h_px = _img.size
    chart_display_h = chart_display_w * _img_h_px / _img_w_px
    buf.seek(0)
    pdf.image(buf, x=10, y=chart_y, w=chart_display_w)
    chart_bottom = chart_y + chart_display_h

    # ---- Table, alongside the chart ----
    table_x = 92
    pdf.set_xy(table_x, chart_y)
    set_pdf_font("B", 11)
    pdf.set_text_color(20, 38, 26)
    pdf.cell(0, 7, L_pdf["pdf_recommended"], ln=True)
    pdf.set_x(table_x)

    pdf.set_fill_color(44, 95, 45)
    pdf.set_text_color(255, 255, 255)
    set_pdf_font("B", 9)
    widths = [60, 18, 30]
    for w, h in zip(widths, [L_pdf["pdf_crop"], L_pdf["pdf_land_pct"], L_pdf["pdf_season"]]):
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()
    pdf.set_x(table_x)
    set_pdf_font("", 9)
    pdf.set_text_color(30, 30, 30)
    fill = False
    for _, row in df.iterrows():
        pdf.set_x(table_x)
        pdf.set_fill_color(244, 247, 239) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(widths[0], 7, crop_disp(row["Crop"]), border=1, fill=True)
        pdf.cell(widths[1], 7, f"{row['Land share (%)']}%", border=1, fill=True)
        pdf.cell(widths[2], 7, str(row["Season"]) if pd.notna(row["Season"]) else "-", border=1, fill=True)
        pdf.ln()
        fill = not fill

    pdf.set_x(table_x)
    set_pdf_font("I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(page_w - table_x - 10, 5, L_pdf["pdf_note"])

    pdf.set_y(max(chart_bottom, pdf.get_y()) + 5)

    # ---- Full sowing window table ----
    set_pdf_font("B", 11)
    pdf.set_text_color(20, 38, 26)
    pdf.cell(0, 8, L_pdf["pdf_sowing"], ln=True)
    pdf.set_fill_color(44, 95, 45)
    pdf.set_text_color(255, 255, 255)
    set_pdf_font("B", 9)
    widths2 = [55, 45, 35, 35]
    for w, h in zip(widths2, [L_pdf["pdf_crop"], L_pdf["pdf_season"], L_pdf["pdf_sow_from"], L_pdf["pdf_sow_to"]]):
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()
    set_pdf_font("", 9)
    pdf.set_text_color(30, 30, 30)
    fill = False
    for _, row in df.iterrows():
        pdf.set_fill_color(244, 247, 239) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(widths2[0], 7, crop_disp(row["Crop"]), border=1, fill=True)
        pdf.cell(widths2[1], 7, str(row["Season"]) if pd.notna(row["Season"]) else "-", border=1, fill=True)
        pdf.cell(widths2[2], 7, str(row["Sow from"]) if pd.notna(row["Sow from"]) else "-", border=1, fill=True)
        pdf.cell(widths2[3], 7, str(row["Sow to"]) if pd.notna(row["Sow to"]) else "-", border=1, fill=True)
        pdf.ln()
        fill = not fill
    pdf.ln(4)

    # ---- Why each crop was chosen ----
    set_pdf_font("B", 11)
    pdf.set_text_color(20, 38, 26)
    pdf.cell(0, 8, L_pdf["pdf_why"], ln=True)
    set_pdf_font("", 9.5)
    pdf.set_text_color(40, 40, 40)
    for _, row in df.iterrows():
        pdf.set_fill_color(244, 247, 239)
        pdf.set_draw_color(151, 188, 98)
        text = f"{crop_disp(row['Crop'])} ({row['Land share (%)']}%): {clean_reason(row['Why'])}"
        pdf.multi_cell(0, 6, text, fill=True, border="L")
        pdf.ln(2)

    # ---- Not recommended ----
    if excluded_rows:
        pdf.ln(2)
        set_pdf_font("B", 11)
        pdf.set_text_color(20, 38, 26)
        pdf.cell(0, 8, L_pdf["pdf_not_rec"], ln=True)
        set_pdf_font("", 9.5)
        pdf.set_text_color(90, 90, 90)
        for crop_name, reason in excluded_rows:
            pdf.multi_cell(0, 6, f"{crop_disp(crop_name)}: {clean_reason(reason)}")
            pdf.ln(1)

    # ---- Language fallback note (only shown when Tamil was requested but
    # no Tamil font was available on the server) ----
    if lang == "ta" and not use_ta:
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 110, 40)
        pdf.multi_cell(0, 5, T["en"]["pdf_tamil_note"])

    # ---- Footer ----
    pdf.set_y(-15)
    if use_ta:
        pdf.set_font("NotoTamil", "", 8)
    else:
        pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 6, L_pdf["pdf_footer"], align="C")

    return bytes(pdf.output())

def _cfg(key, default=""):
    """Database settings come from Streamlit secrets (hosted deployment,
    section [db]) first, then CROP_DB_* environment variables, then the
    local-install defaults, so the same file runs on a laptop and in the cloud."""
    import os
    try:
        if "db" in st.secrets and key in st.secrets["db"]:
            return str(st.secrets["db"][key])
    except Exception:
        pass
    return os.environ.get("CROP_DB_" + key.upper(), default)

HOSTED = bool(_cfg("password"))   # a password in secrets means: public demo, no login box

@st.cache_resource
def get_connection(password):
    return psycopg2.connect(
        dbname=_cfg("dbname", _cfg("name", "crop_allocation")),
        user=_cfg("user", "postgres"),
        password=password,
        host=_cfg("host", "localhost"),
        port=_cfg("port", "5432"),
        sslmode=_cfg("sslmode", "prefer"),
        connect_timeout=int(_cfg("connect_timeout", "15")),
        keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
    )

def ensure_connection(password):
    """Return a healthy cached connection. The cached connection is shared
    across reruns, so it is rolled back at the start of every pass (a failed
    statement would otherwise leave it stuck in an aborted transaction) and
    is rebuilt if the server was restarted in the meantime."""
    conn = get_connection(password)
    try:
        if conn.closed:
            raise psycopg2.InterfaceError("connection closed")
        conn.rollback()
        with conn.cursor() as c:
            c.execute("SELECT 1")
        conn.rollback()
    except Exception:
        get_connection.clear()
        conn = get_connection(password)
    return conn

def run_stage(cur, sql, params=None):
    """Run one pipeline-stage query and return (the exact SQL sent, rows).
    Values are passed as parameters, then merged back in with mogrify only
    for display, so what the farmer sees is literally what the server ran."""
    shown = cur.mogrify(sql, params).decode() if params is not None else sql
    cur.execute(sql, params)
    return shown, cur.fetchall()

def forecast_ci_available(cur):
    """True if PRICE_FORECAST has the interval columns AND at least one row
    has them filled (see forecast_ci_update.py)."""
    try:
        cur.execute("""SELECT COUNT(*) FROM information_schema.columns
                       WHERE table_name = 'price_forecast'
                         AND column_name IN ('forecast_lower', 'forecast_upper')""")
        if cur.fetchone()[0] < 2:
            return False
        cur.execute("SELECT EXISTS (SELECT 1 FROM PRICE_FORECAST WHERE forecast_lower IS NOT NULL AND forecast_upper IS NOT NULL)")
        return bool(cur.fetchone()[0])
    except Exception:
        cur.connection.rollback()
        return False

def render_dashboard(cur, L, lang):
    """Aggregated view across every plan generated so far, not just the
    current farmer. Four live queries, each run for real against the
    database: overall totals, per-crop inclusion/average-share stats, the
    top crop per district (via a RANK() window function), and a
    breakdown of why crops get excluded. This is deliberately separate
    from the single-farmer 'Behind the Scenes' panel above — that one
    explains one farmer's own plan; this one looks across all of them."""
    st.markdown(f"<span class='section-label'>{L['dash_title']}</span>", unsafe_allow_html=True)
    st.caption(L["dash_subtitle"])

    kpi_sql = """SELECT COUNT(DISTINCT ar.request_id), COUNT(DISTINCT f.farmer_id), COUNT(DISTINCT f.district_name)
FROM ALLOCATION_REQUEST ar JOIN FARMER f ON f.farmer_id = ar.farmer_id"""
    cur.execute(kpi_sql)
    total_requests, total_farmers, total_districts = cur.fetchone()

    if not total_requests:
        st.info(L["dash_no_data"])
        return

    crop_sql = """SELECT c.crop_name, COUNT(*) AS times_included, ROUND(AVG(d.land_share_pct),2) AS avg_share
FROM ALLOCATION_DECISION d JOIN CROP c ON c.crop_id = d.crop_id
WHERE d.included = true
GROUP BY c.crop_name
ORDER BY times_included DESC"""
    cur.execute(crop_sql)
    crop_rows = cur.fetchall()

    district_sql = """WITH district_crop_counts AS (
  SELECT f.district_name, c.crop_name, COUNT(*) AS n,
         RANK() OVER (PARTITION BY f.district_name ORDER BY COUNT(*) DESC) AS rnk
  FROM ALLOCATION_DECISION d
  JOIN ALLOCATION_REQUEST ar ON ar.request_id = d.request_id
  JOIN FARMER f ON f.farmer_id = ar.farmer_id
  JOIN CROP c ON c.crop_id = d.crop_id
  WHERE d.included = true
  GROUP BY f.district_name, c.crop_name
)
SELECT district_name, crop_name, n
FROM district_crop_counts
WHERE rnk = 1
ORDER BY district_name"""
    cur.execute(district_sql)
    district_rows = cur.fetchall()

    reason_sql = """SELECT CASE
    WHEN reason_text LIKE 'Excluded: costs%' THEN 'budget'
    WHEN reason_text LIKE 'Excluded: needs%' THEN 'water'
    WHEN reason_text LIKE 'Excluded: recent rainfall%' THEN 'rainfall'
    WHEN reason_text LIKE 'Excluded: no recent market%' THEN 'price'
    WHEN reason_text LIKE 'Excluded: not profitable%' THEN 'score'
    ELSE 'other'
  END AS reason_category, COUNT(*) AS n
FROM ALLOCATION_DECISION
WHERE included = false
GROUP BY reason_category
ORDER BY n DESC"""
    cur.execute(reason_sql)
    reason_rows = cur.fetchall()

    # ---- KPI row ----
    top_crop_overall = crop_label(crop_rows[0][0], lang) if crop_rows else "-"
    metrics = [
        (L["dash_total_requests"], f"{total_requests}"),
        (L["dash_total_farmers"], f"{total_farmers}"),
        (L["dash_districts"], f"{total_districts}"),
        (L["dash_top_crop_overall"], top_crop_overall),
    ]
    mcols = st.columns(4)
    for col, (label, value) in zip(mcols, metrics):
        col.markdown(f"""<div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="font-size:1.15rem;">{value}</div>
        </div>""", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown(f"<span class='section-label'>{L['dash_inclusion_title']}</span>", unsafe_allow_html=True)
        st.caption(L["dash_inclusion_desc"])
        if crop_rows:
            names = [crop_label(r[0], lang) for r in crop_rows]
            counts = [r[1] for r in crop_rows]
            fig, ax = plt.subplots(figsize=(5, 3.2))
            ax.barh(names[::-1], counts[::-1], color=PRIMARY)
            ax.set_xlabel(L["dash_col_times"])
            fig.patch.set_alpha(0)
            st.pyplot(fig, use_container_width=True)
    with right:
        st.markdown(f"<span class='section-label'>{L['dash_share_title']}</span>", unsafe_allow_html=True)
        st.caption(L["dash_share_desc"])
        if crop_rows:
            names = [crop_label(r[0], lang) for r in crop_rows]
            shares = [float(r[2]) if r[2] is not None else 0 for r in crop_rows]
            fig2, ax2 = plt.subplots(figsize=(5, 3.2))
            ax2.barh(names[::-1], shares[::-1], color=ACCENT)
            ax2.set_xlabel("%")
            fig2.patch.set_alpha(0)
            st.pyplot(fig2, use_container_width=True)

    st.markdown(f"<span class='section-label'>{L['dash_district_title']}</span>", unsafe_allow_html=True)
    st.caption(L["dash_district_desc"])
    if district_rows:
        ddf = pd.DataFrame(
            [(d, crop_label(c, lang), n) for d, c, n in district_rows],
            columns=[L["dash_col_district"], L["dash_col_top_crop"], L["dash_col_times"]],
        )
        st.dataframe(ddf, use_container_width=True, hide_index=True)

    st.markdown(f"<span class='section-label'>{L['dash_exclusion_title']}</span>", unsafe_allow_html=True)
    st.caption(L["dash_exclusion_desc"])
    if reason_rows:
        reason_label_key = {
            "budget": "dash_reason_budget", "water": "dash_reason_water",
            "rainfall": "dash_reason_rainfall", "price": "dash_reason_price",
            "score": "dash_reason_score", "other": "dash_reason_other",
        }
        labels = [L[reason_label_key.get(r[0], "dash_reason_other")] for r in reason_rows]
        counts = [r[1] for r in reason_rows]
        fig3, ax3 = plt.subplots(figsize=(6, 3))
        ax3.bar(labels, counts, color=[PRIMARY, ACCENT, "#6E9B4F", "#B4CB8F", "#D69A52", "#8FB57A"][:len(labels)])
        ax3.set_ylabel(L["dash_col_times"])
        fig3.patch.set_alpha(0)
        st.pyplot(fig3, use_container_width=True)

    with st.expander(L["dash_sql_title"]):
        st.caption(L["dash_sql_desc"])
        for sql in (kpi_sql, crop_sql, district_sql, reason_sql):
            st.markdown(f"<div class='sql-box'>{sql}</div>", unsafe_allow_html=True)

if "db_password" not in st.session_state:
    st.session_state.db_password = _cfg("password")
if "lang" not in st.session_state:
    st.session_state.lang = "en"

with st.sidebar:
    lang_choice = st.radio("Language / மொழி", ["English", "தமிழ்"], horizontal=True)
    st.session_state.lang = "ta" if lang_choice == "தமிழ்" else "en"
    L = T[st.session_state.lang]
    st.divider()
    nav_choice = st.radio(L["nav_label"], [L["nav_plan"], L["nav_dashboard"]], horizontal=False)
    st.session_state.view_mode = "dashboard" if nav_choice == L["nav_dashboard"] else "plan"
    st.divider()
    if not HOSTED:
        st.markdown(f"### {L['db']}")
        st.session_state.db_password = st.text_input(L["pw"], type="password", value=st.session_state.db_password)
    st.divider()
    st.markdown(f"**{L['pipeline']}**")
    st.caption(L["pipeline_desc"])
    st.divider()
    st.caption("💡 " + L["sidebar_tip"].format(panel=L["behind_scenes"]))

L = T[st.session_state.lang]
st.markdown(f"""<div class="header-band"><h1>{L['title']}</h1><p>{L['subtitle']}</p></div>""", unsafe_allow_html=True)

if not st.session_state.db_password:
    st.info(L["enter_pw"])
    st.stop()

try:
    conn = ensure_connection(st.session_state.db_password)
    cur = conn.cursor()
except Exception as e:
    st.error(f"{L['db_down']}\n\n{e}")
    st.stop()

# The District Dashboard is a separate view (aggregated across every plan
# generated so far) from the single-farmer plan form below; it fully
# replaces the page's content for this script pass rather than appending
# to it, so it returns before the farmer form is ever built.
if st.session_state.get("view_mode") == "dashboard":
    render_dashboard(cur, L, st.session_state.lang)
    st.markdown(f"<hr style='margin-top:3rem;border-color:#D8E2CC'><p style='text-align:center;color:#5B6E56;font-size:0.8rem'>{L['footer']}</p>", unsafe_allow_html=True)
    st.stop()

_ = cur.execute("SELECT district_name FROM DISTRICT ORDER BY district_name")
districts = [row[0] for row in cur.fetchall()]

st.markdown(f"<span class='section-label'>{L['form_title']}</span>", unsafe_allow_html=True)
if HOSTED:
    st.caption("This is a demo database. Please use a nickname instead of your real name." if st.session_state.lang == "en"
               else "இது ஒரு டெமோ தரவுத்தளம். உங்கள் உண்மையான பெயருக்குப் பதிலாக புனைப்பெயரைப் பயன்படுத்தவும்.")
with st.form("farmer_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
        name = st.text_input(L["name"], key="farmer_name")
        district = st.selectbox(L["district"], districts, index=None, placeholder="Select a district", key="farmer_district")
    with c2:
        season = st.selectbox(L["season"], ["Kharif", "Rabi", "Zaid"], index=None, placeholder="Select a season", key="farmer_season")
        land_acres = st.number_input(L["land"], min_value=0.1, value=None, step=0.5, placeholder=L["land_ph"], key="farmer_land")
    with c3:
        budget_inr = st.number_input(L["budget"], min_value=1000, value=None, step=1000, placeholder=L["budget_ph"], key="farmer_budget")
        water_available = st.number_input(L["water"], min_value=50, value=None, step=50, placeholder=L["water_ph"], key="farmer_water")
    submitted = st.form_submit_button(L["submit"], use_container_width=True)

if submitted:
    name = (name or "").strip()[:80]
    if not name:
        st.warning(L["invalid_name"])
        st.stop()
    if any(v is None for v in (district, season, land_acres, budget_inr, water_available)):
        st.warning(L["missing"])
        st.stop()
    if land_acres > 500:
        st.warning(L["land_big"])

    try:
        _ = cur.execute("INSERT INTO FARMER (name, district_name) VALUES (%s, %s) RETURNING farmer_id", (name, district))
        farmer_id = cur.fetchone()[0]
        _ = cur.execute(
            """INSERT INTO ALLOCATION_REQUEST (farmer_id, request_date, season, land_acres, budget_inr, water_available)
               VALUES (%s, CURRENT_DATE, %s, %s, %s, %s) RETURNING request_id""",
            (farmer_id, season, land_acres, budget_inr, water_available))
        request_id = cur.fetchone()[0]
        _ = conn.commit()
        _ = cur.execute("SELECT run_allocation(%s)", (request_id,))
        _ = conn.commit()

        _ = cur.execute(
            """SELECT crop_name, land_share_pct, score, reason_text, season_name, sowing_start, sowing_end
               FROM farmer_plan WHERE request_id = %s ORDER BY land_share_pct DESC""", (request_id,))
        included_rows = cur.fetchall()
        _ = cur.execute(
            """SELECT c.crop_name, ad.reason_text FROM ALLOCATION_DECISION ad
               JOIN CROP c ON c.crop_id = ad.crop_id
               WHERE ad.request_id = %s AND ad.included = false ORDER BY c.crop_name""", (request_id,))
        excluded_rows = cur.fetchall()
        excluded_rows = [(c, r if r else "") for c, r in excluded_rows]

        # Store the result so it survives the app rerunning for any other
        # reason (like switching language), not just this one script pass.
        st.session_state["last_result"] = {
            "name": name, "district": district, "land_acres": land_acres,
            "budget_inr": budget_inr, "water_available": water_available,
            "included_rows": included_rows, "excluded_rows": excluded_rows,
            "request_id": request_id, "season": season,
        }

    except psycopg2.errors.UndefinedFunction:
        conn.rollback()
        st.error(L["fn_missing"])
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        conn.rollback()
        st.error(L["db_down"])
    except Exception as e:
        conn.rollback()
        st.error(f"Error: {e}")

# Render the most recent result, if one exists — this runs on every
# script pass, including a language switch, not only right after submit.
if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    name, district = r["name"], r["district"]
    land_acres, budget_inr, water_available = r["land_acres"], r["budget_inr"], r["water_available"]
    included_rows, excluded_rows = r["included_rows"], r["excluded_rows"]
    request_id = r["request_id"]
    season_used = r.get("season")

    # Forecast price and its 95% interval for this district, if available.
    fc_info = {}
    has_ci = forecast_ci_available(cur)
    if has_ci:
        try:
            cur.execute("""SELECT c.crop_name, fc.predicted_price, fc.forecast_lower, fc.forecast_upper
                           FROM PRICE_FORECAST fc JOIN CROP c ON c.crop_id = fc.crop_id
                           WHERE fc.district_name = %s""", (district,))
            for cn, pp, lo, hi in cur.fetchall():
                if pp is not None and lo is not None and hi is not None:
                    fc_info[cn] = (float(pp), float(lo), float(hi))
        except Exception:
            conn.rollback()

    st.markdown(f"<span class='section-label'>{L['plan_for']}: {name} — {district}</span>", unsafe_allow_html=True)

    total_crops = len(included_rows) + len(excluded_rows)
    metrics = [
        (L["land_m"], f"{land_acres}"),
        (L["budget_m"], f"{budget_inr:,.0f}"),
        (L["rec_m"], f"{len(included_rows)} / {total_crops}"),
    ]
    mcols = st.columns(3)
    for col, (label, value) in zip(mcols, metrics):
        col.markdown(f"""<div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>""", unsafe_allow_html=True)

    if included_rows:
        top = included_rows[0]
        st.markdown(f"""<div class="hero">
            <div class="label">{L['top_pick']}</div>
            <div class="crop">{crop_label(top[0], st.session_state.lang)}</div>
            <div class="detail">{top[1]}% {L['top_pick_of']} &nbsp;&middot;&nbsp; {clean_reason(top[3])}</div>
        </div>""", unsafe_allow_html=True)

    tab_plan_title = f"{L['your_plan']} ({len(included_rows)})"
    tab_excluded_title = f"{L['not_rec']} ({len(excluded_rows)})"

    st.markdown(f"<span class='section-label'>{tab_plan_title}</span>", unsafe_allow_html=True)
    if included_rows:
        df = pd.DataFrame(included_rows, columns=["Crop", "Land share (%)", "Score", "Why", "Season", "Sow from", "Sow to"])
        df["Label"] = df["Crop"].map(lambda c: crop_label(c, st.session_state.lang))
        df[["Season", "Sow from", "Sow to"]] = df[["Season", "Sow from", "Sow to"]].fillna("-")
        df["Why"] = df["Why"].fillna("")

        left, right = st.columns([1, 1.1])
        with left:
            st.markdown(f"<span class='section-label'>{L['allocation']}</span>", unsafe_allow_html=True)
            fig, ax = plt.subplots(figsize=(4.3, 4.3))
            fig.patch.set_alpha(0)
            palette = ["#2C5F2D", "#6E9B4F", "#97BC62", "#D69A52", "#B4CB8F", "#4A7A3D"]
            colors = [palette[i % len(palette)] for i in range(len(df))]
            # No crop names inside the chart itself: matplotlib has no Tamil
            # glyphs or text shaping, so Tamil names would draw as empty boxes.
            # The legend below is HTML, which the browser shapes correctly.
            wedges, texts, autotexts = ax.pie(
                df["Land share (%)"], autopct="%1.1f%%", pctdistance=0.72,
                colors=colors, startangle=90, textprops={"fontsize": 9, "color": DARK},
                wedgeprops={"edgecolor": "white", "linewidth": 2})
            for at in autotexts:
                at.set_color("white"); at.set_fontweight("bold"); at.set_fontsize(9)
            _ = ax.axis("equal")
            _ = st.pyplot(fig, use_container_width=True)
            plt.close(fig)
            st.markdown(
                "<div style='display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:4px'>" +
                "".join(f"<span style='display:inline-flex;align-items:center;gap:6px;font-size:0.9rem;color:{DARK}'>"
                        f"<span style='width:12px;height:12px;border-radius:3px;background:{c};display:inline-block'></span>"
                        f"{html.escape(str(lbl))}</span>" for c, lbl in zip(colors, df["Label"])) +
                "</div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<span class='section-label'>{L['details']}</span>", unsafe_allow_html=True)
            display_df = df[["Label", "Land share (%)", "Season", "Sow from", "Sow to"]].reset_index(drop=True)
            _ = st.dataframe(display_df, use_container_width=True, hide_index=True)
            try:
                pdf_bytes = build_pdf(name, district, land_acres, budget_inr, water_available, df, excluded_rows, lang=st.session_state.lang)
            except Exception as pdf_err:
                pdf_bytes = None
                st.caption(f"PDF generation failed ({pdf_err}); CSV is still available below.")
            dl1, dl2 = st.columns(2)
            if pdf_bytes:
                _ = dl1.download_button(L["download_pdf"], pdf_bytes, file_name=f"crop_plan_{name.replace(' ','_')}.pdf",
                                     mime="application/pdf", use_container_width=True, key="dl_pdf")
            _ = dl2.download_button(L["download_csv"], df.drop(columns=["Label"]).to_csv(index=False),
                                 file_name=f"crop_plan_{name.replace(' ','_')}.csv", mime="text/csv",
                                 use_container_width=True, key="dl_csv")

        st.markdown(f"<span class='section-label'>{L['why_chosen']}</span>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            band = ""
            if row["Crop"] in fc_info:
                pp, lo, hi = fc_info[row["Crop"]]
                band = (f"<br><span class='sub'>{L['fc_label']}: &#8377;{pp:,.0f} {L['fc_unit']} "
                        f"({L['fc_range']}: &#8377;{lo:,.0f} &ndash; &#8377;{hi:,.0f})</span>")
            st.markdown(f"<div class='why-card'><b>{row['Label']}</b> ({row['Land share (%)']}%) &mdash; {clean_reason(row['Why'])}{band}</div>", unsafe_allow_html=True)
    else:
        st.warning(L["no_crops"])

    st.markdown(f"<span class='section-label'>{tab_excluded_title}</span>", unsafe_allow_html=True)
    if excluded_rows:
        for crop_name, reason in excluded_rows:
            st.markdown(f"<div class='why-card'><b>{crop_label(crop_name, st.session_state.lang)}</b><br><span class='sub'>{clean_reason(reason)}</span></div>", unsafe_allow_html=True)
    else:
        st.success(L["all_included"])

    # ---------------- Behind the Scenes: live SQL, run for real ----------------
    # All 5 pipeline stages are shown, each run for real against the live
    # database (not canned output), open by default so nothing is hidden
    # behind an extra click, with a quick at-a-glance strip up top and a
    # numbered badge + row count on every stage below.
    stage_titles = [L["stage1_title"], L["stage2_title"], L["stage3_title"], L["stage4_title"], L["stage5_title"]]
    with st.expander(L["behind_scenes"], expanded=True):
        st.markdown(
            "<div class='pipeline-strip'>" +
            "".join(f"<div class='pipeline-chip'>{i+1}. {t}</div>" for i, t in enumerate(stage_titles)) +
            "</div>", unsafe_allow_html=True)

        def stage_header(num, title, desc):
            st.markdown(
                f"<div class='step-row'><div class='step-badge'>{num}</div>"
                f"<div class='stage-label'>{title}</div>"
                f"<div class='step-status'>✓ {L['step_done']}</div></div>"
                f"<div class='stage-desc'>{desc}</div>", unsafe_allow_html=True)

        # Stage 1 — Soil eligibility filter
        stage_header(1, L["stage1_title"], L["stage1_desc"])
        stage1_sql = """SELECT c.crop_name, c.ph_min, c.ph_max, d.ph_status
FROM CROP c, DISTRICT d
WHERE d.district_name = %s
  AND ((d.ph_status = 'Acidic'  AND 6.0 BETWEEN c.ph_min AND c.ph_max)
    OR (d.ph_status = 'Neutral' AND 6.8 BETWEEN c.ph_min AND c.ph_max)
    OR (d.ph_status = 'Alkaline' AND 7.8 BETWEEN c.ph_min AND c.ph_max));"""
        shown1, stage1_rows = run_stage(cur, stage1_sql, (district,))
        st.markdown(f"<div class='sql-box'>{html.escape(shown1)}</div>", unsafe_allow_html=True)
        stage1_df = pd.DataFrame(stage1_rows, columns=["Crop", "pH Min", "pH Max", "District Soil"])
        st.markdown(f"<div class='row-count'>{L['run_query']} {len(stage1_rows)} {L['rows_returned']}</div>", unsafe_allow_html=True)
        st.dataframe(stage1_df, use_container_width=True, hide_index=True)

        # Stage 2 — Price forecast (with its 95% interval when available)
        stage_header(2, L["stage2_title"], L["stage2_desc_ci"] if has_ci else L["stage2_desc"])
        if has_ci:
            stage2_sql = """SELECT c.crop_name, fc.predicted_price, fc.forecast_lower, fc.forecast_upper, fc.model_used
FROM PRICE_FORECAST fc JOIN CROP c ON c.crop_id = fc.crop_id
WHERE fc.district_name = %s;"""
            stage2_cols = ["Crop", "Predicted Price", "Lower (95%)", "Upper (95%)", "Model Used"]
        else:
            stage2_sql = """SELECT c.crop_name, fc.predicted_price, fc.model_used
FROM PRICE_FORECAST fc JOIN CROP c ON c.crop_id = fc.crop_id
WHERE fc.district_name = %s;"""
            stage2_cols = ["Crop", "Predicted Price", "Model Used"]
        shown2, stage2_rows = run_stage(cur, stage2_sql, (district,))
        st.markdown(f"<div class='sql-box'>{html.escape(shown2)}</div>", unsafe_allow_html=True)
        stage2_df = pd.DataFrame(stage2_rows, columns=stage2_cols)
        st.markdown(f"<div class='row-count'>{L['run_query']} {len(stage2_rows)} {L['rows_returned']}</div>", unsafe_allow_html=True)
        st.dataframe(stage2_df, use_container_width=True, hide_index=True)

        # Stage 3 — Budget, water and rainfall constraints. This now mirrors
        # run_allocation exactly: the same farm-size discount on cost, and
        # the same seasonal-rainfall rule, so the PASS/FAIL shown here can
        # never disagree with the decision the function actually made.
        stage_header(3, L["stage3_title"], L["stage3_desc"])
        stage3_sql = """WITH farm AS (
  SELECT GREATEST(0.90, 1 - 0.02 * FLOOR(%(land)s / 2)) AS scale_factor,
         (SELECT w.value FROM WEATHER w
          WHERE w.district_name = %(district)s AND w.metric = 'rainfall_pct_departure'
            AND ((%(season)s = 'Kharif' AND w.period LIKE 'SW Monsoon%%')
              OR (%(season)s = 'Rabi'   AND w.period LIKE 'NE Monsoon%%'))
          ORDER BY w.period DESC LIMIT 1) AS rainfall_departure_pct
)
SELECT c.crop_name,
       ROUND(c.cost_per_acre_inr * f.scale_factor * %(land)s) AS total_cost,
       CASE WHEN c.cost_per_acre_inr * f.scale_factor * %(land)s <= %(budget)s THEN 'PASS' ELSE 'FAIL' END AS budget_check,
       c.water_requirement_mm,
       CASE WHEN c.water_requirement_mm <= %(water)s THEN 'PASS' ELSE 'FAIL' END AS water_check,
       CASE WHEN f.rainfall_departure_pct IS NOT NULL AND f.rainfall_departure_pct <= -30
                 AND c.water_requirement_mm > 1000 THEN 'FAIL' ELSE 'PASS' END AS rainfall_check
FROM CROP c CROSS JOIN farm f
ORDER BY total_cost;"""
        shown3, stage3_rows = run_stage(cur, stage3_sql, {
            "land": float(land_acres), "district": district, "season": season_used or "",
            "budget": float(budget_inr), "water": float(water_available)})
        st.markdown(f"<div class='sql-box'>{html.escape(shown3)}</div>", unsafe_allow_html=True)
        stage3_df = pd.DataFrame(stage3_rows, columns=["Crop", "Total Cost (Rs.)", "Budget Check", "Water Need (mm)", "Water Check", "Rainfall Check"])
        st.markdown(f"<div class='row-count'>{L['run_query']} {len(stage3_rows)} {L['rows_returned']}</div>", unsafe_allow_html=True)
        st.dataframe(stage3_df, use_container_width=True, hide_index=True)

        # Stage 4 — Blended scoring & land split
        stage_header(4, L["stage4_title"], L["stage4_desc"])
        stage4_sql = """SELECT crop_name, land_share_pct, score, reason_text
FROM farmer_plan WHERE request_id = %s ORDER BY land_share_pct DESC;"""
        shown4, stage4_rows = run_stage(cur, stage4_sql, (request_id,))
        st.markdown(f"<div class='sql-box'>SELECT run_allocation({int(request_id)});  -- already executed when the plan was created\n{html.escape(shown4)}</div>", unsafe_allow_html=True)
        stage4_df = pd.DataFrame(stage4_rows, columns=["Crop", "Land Share %", "Score", "Reason"])
        st.markdown(f"<div class='row-count'>{L['run_query']} {len(stage4_rows)} {L['rows_returned']}</div>", unsafe_allow_html=True)
        st.dataframe(stage4_df, use_container_width=True, hide_index=True)

        # Stage 5 — Full audit log (included AND excluded crops, real table, not the view)
        stage_header(5, L["stage5_title"], L["stage5_desc"])
        stage5_sql = """SELECT c.crop_name, ad.included, ad.land_share_pct, ad.score, ad.reason_text
FROM ALLOCATION_DECISION ad JOIN CROP c ON c.crop_id = ad.crop_id
WHERE ad.request_id = %s
ORDER BY ad.included DESC, ad.land_share_pct DESC;"""
        shown5, stage5_rows = run_stage(cur, stage5_sql, (request_id,))
        st.markdown(f"<div class='sql-box'>{html.escape(shown5)}</div>", unsafe_allow_html=True)
        stage5_df = pd.DataFrame(stage5_rows, columns=["Crop", "Included", "Land Share %", "Score", "Reason"])
        st.markdown(f"<div class='row-count'>{L['run_query']} {len(stage5_rows)} {L['rows_returned']}</div>", unsafe_allow_html=True)
        st.dataframe(stage5_df, use_container_width=True, hide_index=True)

st.markdown(f"<hr style='margin-top:3rem;border-color:#D8E2CC'><p style='text-align:center;color:#5B6E56;font-size:0.8rem'>{L['footer']}</p>", unsafe_allow_html=True)
