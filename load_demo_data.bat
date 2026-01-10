@echo off
REM Load realistic demo data for testing

title Loading Demo Data

echo.
echo ==========================================
echo   Loading Realistic Demo Data
echo ==========================================
echo.

call venv\Scripts\activate.bat

python -c "from voice_time.database.schema import init_db; from voice_time.database.sample_data import create_realistic_matters, create_sample_day_plan; from voice_time.config import Config; config = Config.load(); session = init_db(config.data_dir / 'voice_time.db'); matters = create_realistic_matters(session); plan = create_sample_day_plan(session); print(f'\n✓ Created {len(matters)} realistic matters'); print('✓ Created sample day plan with tasks'); print('\nDemo data loaded! Run the app to see it.')"

echo.
echo ==========================================
echo   Demo Data Ready!
echo ==========================================
echo.
echo The app now has:
echo   • 12 realistic legal matters
echo   • Today's sample plan with tasks
echo   • Multiple practice areas
echo   • Realistic aliases for testing
echo.
echo Run the app and check the Tutorial page!
echo.

pause
