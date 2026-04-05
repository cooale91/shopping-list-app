@echo off
cd /d "%USERPROFILE%\Documents\shopping_list_app_v4"
python -m streamlit run app.py --server.address 0.0.0.0
pause
