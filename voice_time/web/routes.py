"""Flask routes for web UI."""
from flask import render_template, request, jsonify, current_app
from datetime import date, datetime
from pathlib import Path
import math
from ..database.models import Matter, PlannedTask, WorkLog, DayPlan, ActiveTimer, ActivityType


def register_routes(app):
    """Register all routes with the Flask app."""
    
    @app.route('/landing')
    def landing():
        """Beautiful landing page."""
        return render_template('landing.html')
    
    @app.route('/app')
    def app_interface():
        """Main app interface (redirect from landing)."""
        return index()
    
    @app.route('/tutorial')
    def tutorial():
        """Tutorial and testing page."""
        from ..database.sample_data import TUTORIAL_SCENARIOS
        return render_template('tutorial.html', scenarios=TUTORIAL_SCENARIOS)
    
    @app.route('/how-it-works')
    def how_it_works():
        """How It Works page - explains the technology and approach."""
        return render_template('how-it-works.html')
    
    @app.route('/planning')
    def planning():
        """Day planning page - separate from time recording."""
        from datetime import timedelta
        from ..database.models import MemoAction
        session = app.session
        
        # Get selected date from query param, default to today
        today = date.today()
        date_str = request.args.get('date')
        
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = today
        else:
            selected_date = today
        
        is_today = selected_date == today
        
        # Get plan for selected date
        plan = session.query(DayPlan).filter(DayPlan.date == selected_date).first()
        
        tasks = []
        if plan:
            tasks = session.query(PlannedTask).filter(
                PlannedTask.day_plan_id == plan.id
            ).order_by(PlannedTask.sort_order).all()
        
        # Pre-calculate dates for navigation
        prev_date = selected_date - timedelta(days=1)
        next_date = selected_date + timedelta(days=1)
        
        # Get matters and activities for dropdowns
        matters = session.query(Matter).filter(Matter.is_active == True).all()
        activities = session.query(ActivityType).all()
        
        # Get today's work summary
        next_day = selected_date + timedelta(days=1)
        logs = session.query(WorkLog).filter(
            WorkLog.created_at >= selected_date,
            WorkLog.created_at < next_day
        ).all()
        
        totals = {}
        total_hours = 0.0
        for log in logs:
            matter_name = log.matter.display_name if log.matter else 'General'
            totals[matter_name] = totals.get(matter_name, 0) + log.duration_hours
            total_hours += log.duration_hours
        
        # Get pending actions from Voice Memos (due today or earlier, not completed)
        pending_actions = session.query(MemoAction).filter(
            MemoAction.is_completed == False,
            MemoAction.due_date <= selected_date
        ).order_by(MemoAction.created_at.desc()).all()
        
        # Get incomplete tasks from previous days (carryover)
        carryover_tasks = []
        if is_today:
            # Find all incomplete tasks from plans before today
            carryover_tasks = session.query(PlannedTask).join(DayPlan).filter(
                DayPlan.date < today,
                PlannedTask.status.in_(['pending', 'planned', 'in_progress'])
            ).order_by(DayPlan.date.desc()).all()
        
        return render_template(
            'planning.html', 
            tasks=tasks,
            matters=matters,
            activities=activities,
            totals=totals,
            total_hours=total_hours,
            selected_date=selected_date,
            is_today=is_today,
            today=today,
            prev_date=prev_date,
            next_date=next_date,
            pending_actions=pending_actions,
            carryover_tasks=carryover_tasks
        )
    
    @app.route('/why')
    def why():
        """Why TimeBrief? - Comparison page."""
        return render_template('why.html')
    
    @app.route('/review')
    def review():
        """Review and edit time entries for a specific day."""
        from datetime import timedelta
        session = app.session
        
        # Get selected date from query param, default to today
        today = date.today()
        date_str = request.args.get('date')
        
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = today
        else:
            selected_date = today
        
        is_today = selected_date == today
        
        # Get work logs for selected date
        next_day = selected_date + timedelta(days=1)
        logs = session.query(WorkLog).filter(
            WorkLog.created_at >= selected_date,
            WorkLog.created_at < next_day
        ).order_by(WorkLog.created_at.desc()).all()
        
        # Calculate totals by matter
        totals = {}
        total_hours = 0.0
        for log in logs:
            matter_name = log.matter.display_name if log.matter else "General"
            if matter_name not in totals:
                totals[matter_name] = 0.0
            totals[matter_name] += log.duration_hours
            total_hours += log.duration_hours
        
        # Pre-calculate dates for navigation
        prev_date = selected_date - timedelta(days=1)
        next_date = selected_date + timedelta(days=1)
        
        # Get matters and activities for editing
        matters = session.query(Matter).filter(Matter.is_active == True).order_by(Matter.display_name).all()
        activities = session.query(ActivityType).order_by(ActivityType.display_order).all()
        
        return render_template(
            'review.html',
            logs=logs,
            totals=totals,
            total_hours=total_hours,
            selected_date=selected_date,
            is_today=is_today,
            today=today,
            prev_date=prev_date,
            next_date=next_date,
            matters=matters,
            activities=activities
        )
    
    @app.route('/chat')
    def chat_page():
        """AI Chat page for querying your data."""
        return render_template('chat.html')
    
    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        """Chat with AI assistant about your matters and time entries."""
        from ..llm.assistant import GroundedAssistant
        from ..llm.client import OllamaClient
        
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'response': 'Please ask a question.'})
        
        try:
            llm = OllamaClient(app.config_obj.ollama)
            assistant = GroundedAssistant(llm, app.session)
            result = assistant.chat(query)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'response': f'Error: {str(e)}'})
    
    @app.route('/api/ai/day-summary')
    def api_day_summary():
        """Generate AI summary of today's work."""
        from ..llm.assistant import GroundedAssistant
        from ..llm.client import OllamaClient
        
        try:
            llm = OllamaClient(app.config_obj.ollama)
            assistant = GroundedAssistant(llm, app.session)
            result = assistant.generate_day_summary()
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'summary': f'Error: {str(e)}'})
    
    @app.route('/api/ai/client-update', methods=['POST'])
    def api_client_update():
        """Generate draft client update email for a matter."""
        from ..llm.assistant import GroundedAssistant
        from ..llm.client import OllamaClient
        
        data = request.json
        matter_name = data.get('matter', '').strip()
        
        if not matter_name:
            return jsonify({'success': False, 'email': 'Please specify a matter name.'})
        
        try:
            llm = OllamaClient(app.config_obj.ollama)
            assistant = GroundedAssistant(llm, app.session)
            result = assistant.generate_client_update(matter_name)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'email': f'Error: {str(e)}'})
    
    @app.route('/api/ai/suggest-next')
    def api_suggest_next():
        """Get AI suggestion for what to work on next."""
        from ..llm.assistant import GroundedAssistant
        from ..llm.client import OllamaClient
        
        try:
            llm = OllamaClient(app.config_obj.ollama)
            assistant = GroundedAssistant(llm, app.session)
            result = assistant.suggest_next_task()
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'suggestion': f'Error: {str(e)}'})
    
    @app.route('/api/ai/week-analysis')
    def api_week_analysis():
        """Get AI analysis of the week's time distribution."""
        from ..llm.assistant import GroundedAssistant
        from ..llm.client import OllamaClient
        
        try:
            llm = OllamaClient(app.config_obj.ollama)
            assistant = GroundedAssistant(llm, app.session)
            result = assistant.analyze_week()
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'analysis': f'Error: {str(e)}'})
    
    @app.route('/check-ollama')
    def check_ollama():
        """Check if Ollama is running and model is available."""
        from ..llm.client import OllamaClient
        
        llm_client = OllamaClient(app.config_obj.ollama)
        
        # Check if Ollama is reachable
        is_running = llm_client.health_check()
        
        if is_running:
            # Try a test generation
            try:
                result = llm_client.generate(
                    "Say 'test'",
                    json_mode=False,
                    temperature=0.1
                )
                return jsonify({
                    'status': 'ready',
                    'running': True,
                    'model': app.config_obj.ollama.model,
                    'test_response': result.get('text', '')[:100],
                    'message': 'Ollama is ready and responding'
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'running': True,
                    'model': app.config_obj.ollama.model,
                    'error': str(e),
                    'message': 'Ollama is running but model not responding'
                })
        else:
            return jsonify({
                'status': 'not_running',
                'running': False,
                'message': 'Ollama server is not running',
                'fix': 'Run: ollama serve'
            })
    
    @app.route('/settings')
    def settings():
        """Settings and voice diagnostics page."""
        return render_template('settings.html')
    
    @app.route('/test-whisper', methods=['POST'])
    def test_whisper():
        """Detailed Whisper model testing with diagnostics."""
        import tempfile
        import os
        
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'stage': 'upload',
                'error': 'No audio file provided'
            })
        
        audio_file = request.files['audio']
        tmp_path = None
        
        try:
            # Stage 1: Save audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
                tmp_path = tmp.name
            
            audio_file.save(tmp_path)
            file_size = os.path.getsize(tmp_path)
            
            result = {
                'success': True,
                'stage': 'saved',
                'file_size': file_size,
                'file_path': tmp_path
            }
            
            if file_size < 1000:
                result['warning'] = 'Audio file very small - may be too short'
            
            # Stage 2: Create Transcriber (doesn't load model yet)
            from ..voice.transcribe import Transcriber
            
            result['stage'] = 'creating_transcriber'
            result['model'] = app.config_obj.whisper.model
            result['device'] = app.config_obj.whisper.device
            
            transcriber = Transcriber(
                model_size=app.config_obj.whisper.model,
                device=app.config_obj.whisper.device
            )
            
            # Load vocabulary from database to improve recognition
            session = app.session
            matters = session.query(Matter).filter(Matter.is_active == True).all()
            matter_vocab = []
            for m in matters:
                matter_vocab.append(m.display_name)
                if m.client:
                    matter_vocab.append(m.client)
                for alias in (m.aliases or []):
                    matter_vocab.append(alias.alias)
            
            activities = session.query(ActivityType).all()
            activity_vocab = [a.label for a in activities]
            
            # Add today's planned tasks to vocabulary
            today = date.today()
            plan = session.query(DayPlan).filter(DayPlan.date == today).first()
            task_vocab = []
            if plan:
                tasks = session.query(PlannedTask).filter(PlannedTask.day_plan_id == plan.id).all()
                for task in tasks:
                    if task.title:
                        task_vocab.append(task.title)
                        task_vocab.extend(task.title.split())
            
            full_vocab = matter_vocab + task_vocab
            transcriber.set_vocabulary(full_vocab, activity_vocab)
            result['vocabulary_loaded'] = len(full_vocab)
            result['planned_tasks_loaded'] = len(task_vocab)
            
            result['stage'] = 'transcriber_created'
            
            # Stage 3: Transcribe (model loads HERE on first use)
            result['stage'] = 'transcribing'
            
            try:
                transcript = transcriber.transcribe_file(tmp_path)
                result['stage'] = 'complete'
                result['transcript'] = transcript
                result['transcript_length'] = len(transcript)
                
                if not transcript or len(transcript) < 3:
                    result['warning'] = 'Transcript very short or empty - speak louder/clearer'
                
                return jsonify(result)
                
            except Exception as e:
                error_str = str(e).lower()
                
                # BUG FIX: Detect model loading errors vs transcription errors
                if 'model' in error_str or 'download' in error_str or 'not found' in error_str:
                    return jsonify({
                        'success': False,
                        'stage': 'model_load_failed',
                        'error': str(e),
                        'file_size': file_size,
                        'fix': 'Whisper model downloading now (first use only). Wait 1-2 minutes and try again.'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'stage': 'transcription_failed',
                        'error': str(e),
                        'file_size': file_size,
                        'fix': 'Try speaking louder and clearer, or check audio format'
                    })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'stage': 'error',
                'error': str(e)
            })
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
    
    @app.route('/api/whisper-models')
    def get_whisper_models():
        """Get available Whisper models."""
        models = [
            {
                'id': 'tiny.en',
                'name': 'Tiny (English)',
                'size': '39 MB',
                'speed': 'Fastest',
                'accuracy': 'Basic',
                'description': 'Very fast but less accurate. Good for simple commands.'
            },
            {
                'id': 'base.en',
                'name': 'Base (English)',
                'size': '74 MB', 
                'speed': 'Fast',
                'accuracy': 'Good',
                'description': 'Good balance of speed and accuracy. Recommended for most users.'
            },
            {
                'id': 'small.en',
                'name': 'Small (English)',
                'size': '244 MB',
                'speed': 'Medium',
                'accuracy': 'Better',
                'description': 'Better accuracy for complex phrases and names.'
            },
            {
                'id': 'medium.en',
                'name': 'Medium (English)',
                'size': '769 MB',
                'speed': 'Slower',
                'accuracy': 'High',
                'description': 'High accuracy. Good if you have issues with names.'
            },
            {
                'id': 'large-v2',
                'name': 'Large v2 (Multilingual)',
                'size': '1.5 GB',
                'speed': 'Slowest',
                'accuracy': 'Best',
                'description': 'Best accuracy. Requires more RAM and download time.'
            }
        ]
        
        return jsonify({
            'models': models,
            'current': app.config_obj.whisper.model
        })
    
    @app.route('/api/whisper-model', methods=['POST'])
    def set_whisper_model():
        """Switch Whisper model (requires app restart to take full effect)."""
        import yaml
        
        data = request.json
        new_model = data.get('model')
        
        valid_models = ['tiny.en', 'base.en', 'small.en', 'medium.en', 'large-v2']
        if new_model not in valid_models:
            return jsonify({'success': False, 'message': f'Invalid model: {new_model}'})
        
        # Update config in memory
        app.config_obj.whisper.model = new_model
        
        # Update config.yaml file
        config_path = Path('config.yaml')
        if config_path.exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}
            
            if 'whisper' not in config_data:
                config_data['whisper'] = {}
            config_data['whisper']['model'] = new_model
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
        
        # Clear cached transcriber so it reloads with new model
        if hasattr(app, 'transcriber'):
            app.transcriber = None
        
        return jsonify({
            'success': True,
            'message': f'Model changed to {new_model}. The new model will be downloaded on first use.',
            'model': new_model
        })
    
    @app.route('/api/llm-models')
    def get_llm_models():
        """Get available Ollama LLM models."""
        models = [
            {
                'id': 'qwen2.5:0.5b-instruct',
                'name': 'Qwen 2.5 0.5B',
                'size': '~400 MB',
                'speed': 'Fastest',
                'quality': 'Basic',
                'description': 'Ultra-fast for simple tasks. May struggle with complex parsing.'
            },
            {
                'id': 'qwen2.5:1.5b-instruct',
                'name': 'Qwen 2.5 1.5B',
                'size': '~1 GB',
                'speed': 'Fast',
                'quality': 'Good',
                'description': 'Good balance. Recommended for most users.'
            },
            {
                'id': 'qwen2.5:3b-instruct',
                'name': 'Qwen 2.5 3B',
                'size': '~2 GB',
                'speed': 'Medium',
                'quality': 'Better',
                'description': 'Better understanding of complex instructions.'
            },
            {
                'id': 'qwen2.5:7b-instruct',
                'name': 'Qwen 2.5 7B',
                'size': '~4.5 GB',
                'speed': 'Slower',
                'quality': 'High',
                'description': 'High quality responses. Good for complex planning.'
            },
            {
                'id': 'llama3.2:3b',
                'name': 'Llama 3.2 3B',
                'size': '~2 GB',
                'speed': 'Medium',
                'quality': 'Good',
                'description': 'Meta\'s latest small model. Good general performance.'
            },
            {
                'id': 'mistral:7b',
                'name': 'Mistral 7B',
                'size': '~4 GB',
                'speed': 'Slower',
                'quality': 'High',
                'description': 'Excellent reasoning. Popular choice for local AI.'
            }
        ]
        
        return jsonify({
            'models': models,
            'current': app.config_obj.ollama.model
        })
    
    @app.route('/api/llm-model', methods=['POST'])
    def set_llm_model():
        """Switch Ollama LLM model - pulls if needed."""
        import yaml
        import subprocess
        
        data = request.json
        new_model = data.get('model')
        
        if not new_model:
            return jsonify({'success': False, 'message': 'No model specified'})
        
        # Update config in memory
        old_model = app.config_obj.ollama.model
        app.config_obj.ollama.model = new_model
        
        # Update config.yaml file
        config_path = Path('config.yaml')
        if config_path.exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}
            
            if 'ollama' not in config_data:
                config_data['ollama'] = {}
            config_data['ollama']['model'] = new_model
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
        
        # Pull the model synchronously so user knows when it's ready
        try:
            result = subprocess.run(
                ['ollama', 'pull', new_model],
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )
            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': f'Model {new_model} ready!',
                    'model': new_model,
                    'downloaded': True
                })
            else:
                return jsonify({
                    'success': True,
                    'message': f'Config saved but download failed: {result.stderr[:100]}',
                    'model': new_model,
                    'downloaded': False
                })
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': True,
                'message': 'Download taking too long - continuing in background',
                'model': new_model,
                'downloaded': False
            })
        except Exception as e:
            return jsonify({
                'success': True,
                'message': f'Config saved. Run "ollama pull {new_model}" manually.',
                'model': new_model,
                'downloaded': False,
                'error': str(e)
            })
    
    @app.route('/api/hardware')
    def get_hardware():
        """Detect hardware for model recommendations."""
        import platform
        import os
        
        hw = {
            'cpu': platform.processor() or 'Unknown',
            'ram_gb': 0,
            'gpu': None,
            'vram_gb': 0,
            'recommended_llm': 'qwen2.5:1.5b-instruct',
            'recommended_whisper': 'base.en'
        }
        
        # Get RAM
        try:
            import psutil
            hw['ram_gb'] = round(psutil.virtual_memory().total / (1024**3))
        except:
            pass
        
        # Check for NVIDIA GPU
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(',')
                hw['gpu'] = parts[0].strip()
                hw['vram_gb'] = round(int(parts[1].strip()) / 1024) if len(parts) > 1 else 0
        except:
            pass
        
        # Recommendations based on hardware
        vram = hw['vram_gb']
        ram = hw['ram_gb']
        
        if vram >= 8:
            hw['recommended_llm'] = 'qwen2.5:7b-instruct'
            hw['recommended_whisper'] = 'medium.en'
            hw['tier'] = 'high'
        elif vram >= 4 or ram >= 32:
            hw['recommended_llm'] = 'qwen2.5:3b-instruct'
            hw['recommended_whisper'] = 'small.en'
            hw['tier'] = 'medium'
        elif ram >= 16:
            hw['recommended_llm'] = 'qwen2.5:1.5b-instruct'
            hw['recommended_whisper'] = 'base.en'
            hw['tier'] = 'standard'
        else:
            hw['recommended_llm'] = 'qwen2.5:0.5b-instruct'
            hw['recommended_whisper'] = 'tiny.en'
            hw['tier'] = 'basic'
        
        return jsonify(hw)
    
    @app.route('/api/llm-test', methods=['POST'])
    def test_llm():
        """Test the current LLM model with a simple prompt."""
        from ..llm.client import OllamaClient
        
        try:
            llm = OllamaClient(app.config_obj.ollama)
            
            # Simple test
            result = llm.generate(
                "Extract the matter name from: 'working on Acme case'. Reply with just the matter name.",
                json_mode=False,
                temperature=0.1
            )
            
            return jsonify({
                'success': True,
                'model': app.config_obj.ollama.model,
                'response': result.get('text', '')[:200],
                'message': 'LLM is responding'
            })
        except Exception as e:
            error_str = str(e)
            # Check if model needs downloading
            if '404' in error_str or 'not found' in error_str.lower():
                return jsonify({
                    'success': False,
                    'model': app.config_obj.ollama.model,
                    'error': f'Model not downloaded yet. Run: ollama pull {app.config_obj.ollama.model}',
                    'needs_download': True,
                    'message': 'Model needs to be downloaded first'
                })
            return jsonify({
                'success': False,
                'model': app.config_obj.ollama.model,
                'error': str(e),
                'message': 'LLM test failed'
            })
    
    @app.route('/api/calendar')
    def get_calendar_data():
        """Get calendar data for a month - which days have entries."""
        from datetime import timedelta
        from sqlalchemy import func, extract
        
        session = app.session
        
        # Get year and month from params, default to current
        year = request.args.get('year', type=int, default=date.today().year)
        month = request.args.get('month', type=int, default=date.today().month)
        
        # Get all days in month that have work logs
        days_with_logs = session.query(
            func.date(WorkLog.created_at).label('day'),
            func.sum(WorkLog.duration_hours).label('hours')
        ).filter(
            extract('year', WorkLog.created_at) == year,
            extract('month', WorkLog.created_at) == month
        ).group_by(
            func.date(WorkLog.created_at)
        ).all()
        
        # Get all days with plans
        days_with_plans = session.query(DayPlan.date).filter(
            extract('year', DayPlan.date) == year,
            extract('month', DayPlan.date) == month
        ).all()
        
        # Build response
        log_days = {str(row.day): round(row.hours, 1) for row in days_with_logs}
        plan_days = [str(row.date) for row in days_with_plans]
        
        return jsonify({
            'year': year,
            'month': month,
            'days_with_logs': log_days,  # {date: hours}
            'days_with_plans': plan_days,
            'today': str(date.today())
        })
    
    @app.route('/api/week-summary')
    def get_week_summary():
        """Get summary of hours for the current week."""
        from datetime import timedelta
        
        session = app.session
        
        # Get date from param or today
        date_str = request.args.get('date')
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = date.today()
        else:
            selected_date = date.today()
        
        # Calculate week boundaries (Monday to Sunday)
        week_start = selected_date - timedelta(days=selected_date.weekday())
        week_end = week_start + timedelta(days=7)
        
        # Get logs for the week
        logs = session.query(WorkLog).filter(
            WorkLog.created_at >= week_start,
            WorkLog.created_at < week_end
        ).all()
        
        # Group by day
        daily_hours = {}
        for log in logs:
            day = log.created_at.date() if log.created_at else log.started_at.date() if log.started_at else None
            if day:
                day_str = str(day)
                if day_str not in daily_hours:
                    daily_hours[day_str] = 0.0
                daily_hours[day_str] += log.duration_hours
        
        return jsonify({
            'week_start': str(week_start),
            'week_end': str(week_end - timedelta(days=1)),
            'daily_hours': daily_hours,
            'total_hours': round(sum(daily_hours.values()), 1)
        })
    
    @app.route('/whisper-status')
    def whisper_status():
        """Check if Whisper model is working and show hardware info."""
        try:
            from ..voice.transcribe import Transcriber
            from ..voice.hardware import detect_hardware, get_optimal_whisper_config
            
            # Detect hardware
            hw = detect_hardware()
            optimal = get_optimal_whisper_config(hw)
            
            # Try to create transcriber with optimal settings
            transcriber = Transcriber(
                model_size=app.config_obj.whisper.model,
                device=optimal['device'],
                compute_type=optimal['compute_type']
            )
            
            # Force model load to verify it works
            try:
                transcriber._ensure_loaded()
                model_status = 'loaded'
                model_message = 'Model is loaded and ready'
            except Exception as e:
                model_status = 'not_loaded'
                model_message = f'Model will download on first use (error: {str(e)})'
            
            return jsonify({
                'status': 'ready',
                'model': app.config_obj.whisper.model,
                'device': optimal['device'],
                'compute_type': optimal['compute_type'],
                'model_status': model_status,
                'message': model_message,
                'hardware': {
                    'cpu': hw['cpu_name'],
                    'has_cuda': hw['has_cuda'],
                    'has_amd': hw['has_amd'],
                    'has_npu': hw['has_npu'],
                    'notes': hw['notes']
                }
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e),
                'message': 'Whisper initialization failed'
            })
    
    @app.route('/')
    def index():
        """Main dashboard with optional date parameter."""
        from datetime import timedelta
        session = app.session
        
        # Get selected date from query param, default to today
        today = date.today()
        date_str = request.args.get('date')
        
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = today
        else:
            selected_date = today
        
        is_today = selected_date == today
        
        # Get plan for selected date
        plan = session.query(DayPlan).filter(DayPlan.date == selected_date).first()
        
        tasks = []
        if plan:
            tasks = session.query(PlannedTask).filter(
                PlannedTask.day_plan_id == plan.id
            ).all()
        
        # Get work logs for selected date
        next_day = selected_date + timedelta(days=1)
        logs = session.query(WorkLog).filter(
            WorkLog.created_at >= selected_date,
            WorkLog.created_at < next_day
        ).order_by(WorkLog.created_at.desc()).all()
        
        # Get active timer only for today
        active_timer = None
        if is_today:
            active_timer = session.query(ActiveTimer).first()
        
        # Calculate totals by matter
        totals = {}
        total_hours = 0.0
        for log in logs:
            matter_name = log.matter.display_name if log.matter else "General"
            if matter_name not in totals:
                totals[matter_name] = 0.0
            totals[matter_name] += log.duration_hours
            total_hours += log.duration_hours
        
        # Get all matters for timer dropdown
        matters = session.query(Matter).filter(Matter.is_active == True).order_by(Matter.last_used_at.desc()).all()
        
        # Get activity types
        activities = session.query(ActivityType).order_by(ActivityType.display_order).all()
        
        # Calculate week dates for navigation
        week_start = selected_date - timedelta(days=selected_date.weekday())  # Monday
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        
        # Pre-calculate prev/next dates for template
        prev_date = selected_date - timedelta(days=1)
        next_date = selected_date + timedelta(days=1)
        
        return render_template(
            'index.html',
            tasks=tasks,
            logs=logs,
            totals=totals,
            total_hours=total_hours,
            active_timer=active_timer,
            matters=matters,
            activities=activities,
            selected_date=selected_date,
            is_today=is_today,
            week_dates=week_dates,
            today=today,
            prev_date=prev_date,
            next_date=next_date
        )
    
    @app.route('/process', methods=['POST'])
    def process():
        """Process text input."""
        data = request.json
        utterance = data.get('utterance', '')
        
        if not utterance:
            return jsonify({
                'success': False,
                'message': 'No input provided'
            })
        
        # Process through state machine
        result = app.day_state.process(utterance)
        
        # Build response with safe data
        response = {
            'success': result.success,
            'message': result.message,
            'needs_clarification': result.needs_clarification,
            'clarification_question': result.clarification_question
        }
        
        # Add safe data fields if present
        if result.data:
            if 'suggestions' in result.data:
                response['suggestions'] = result.data['suggestions']
            if 'available' in result.data:
                response['available'] = result.data['available']
        
        return jsonify(response)
    
    @app.route('/process-voice', methods=['POST'])
    def process_voice():
        """Process voice input from browser."""
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No audio file provided'
            })
        
        audio_file = request.files['audio']
        
        # BUG FIX #2 & #3: Proper temp file handling with cleanup
        import tempfile
        import os
        from ..voice.transcribe import Transcriber
        
        tmp_path = None
        try:
            # Create temp file and get path, then close it (BUG FIX #2)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
                tmp_path = tmp.name
            # File is now closed, safe to write on Windows
            
            # Save audio to the closed temp file
            audio_file.save(tmp_path)
            
            # Transcribe with vocabulary hints for better matter recognition
            transcriber = Transcriber(
                model_size=app.config_obj.whisper.model,
                device=app.config_obj.whisper.device
            )
            
            # Load vocabulary from database to improve recognition
            session = app.session
            matters = session.query(Matter).filter(Matter.is_active == True).all()
            matter_vocab = []
            for m in matters:
                matter_vocab.append(m.display_name)
                matter_vocab.append(m.client)
                if m.aliases:
                    matter_vocab.extend([alias.alias for alias in m.aliases])
            
            activities = session.query(ActivityType).all()
            activity_vocab = [a.label for a in activities]
            
            # Add today's planned tasks to vocabulary for better recognition
            today = date.today()
            plan = session.query(DayPlan).filter(DayPlan.date == today).first()
            task_vocab = []
            if plan:
                tasks = session.query(PlannedTask).filter(PlannedTask.day_plan_id == plan.id).all()
                for task in tasks:
                    # Add task titles (e.g., "write letter to opposing counsel")
                    if task.title:
                        task_vocab.append(task.title)
                        # Also add individual words from task
                        task_vocab.extend(task.title.split())
            
            # Combine all vocabulary
            full_vocab = matter_vocab + task_vocab
            transcriber.set_vocabulary(full_vocab, activity_vocab)
            
            transcript = transcriber.transcribe_file(tmp_path)
            
            if not transcript or not transcript.strip():
                return jsonify({
                    'success': False,
                    'message': 'No speech detected',
                    'transcript': ''
                })
            
            # Process through state machine
            result = app.day_state.process(transcript)
            
            # Build response with safe data
            response = {
                'success': result.success,
                'message': result.message,
                'transcript': transcript,
                'needs_clarification': result.needs_clarification,
                'clarification_question': result.clarification_question
            }
            
            # Add safe data fields if present
            if result.data:
                if 'suggestions' in result.data:
                    response['suggestions'] = result.data['suggestions']
                if 'available' in result.data:
                    response['available'] = result.data['available']
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error processing voice: {str(e)}',
                'transcript': ''
            })
        finally:
            # BUG FIX #3: Always clean up temp file, even on exception
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass  # Best effort cleanup
    
    @app.route('/mic-test')
    def mic_test():
        """Test microphone access."""
        return jsonify({'status': 'ready'})
    
    @app.route('/matters')
    def matters():
        """Matter management page."""
        session = app.session
        matters = session.query(Matter).order_by(Matter.is_active.desc(), Matter.last_used_at.desc()).all()
        return render_template('matters.html', matters=matters)
    
    @app.route('/matters/list')
    def matters_list():
        """List all active matters (API)."""
        session = app.session
        matters = session.query(Matter).filter(Matter.is_active == True).all()
        
        return jsonify({
            'matters': [
                {
                    'id': m.id,
                    'display_name': m.display_name,
                    'matter_ref': m.matter_ref,
                    'client': m.client
                }
                for m in matters
            ]
        })
    
    @app.route('/matters/add', methods=['POST'])
    def add_matter():
        """Add a new matter."""
        data = request.json
        session = app.session
        
        try:
            from ..database.models import Matter, MatterAlias
            
            # Create matter
            matter = Matter(
                matter_ref=data.get('matter_ref'),
                display_name=data['display_name'],
                client=data.get('client'),
                is_active=True
            )
            session.add(matter)
            session.flush()
            
            # Add aliases
            for alias_text in data.get('aliases', []):
                if alias_text.strip():
                    alias = MatterAlias(
                        matter_id=matter.id,
                        alias=alias_text.strip(),
                        is_primary=False
                    )
                    session.add(alias)
            
            session.commit()
            
            return jsonify({'success': True, 'matter_id': matter.id})
            
        except Exception as e:
            session.rollback()
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/matters/archive/<matter_id>', methods=['POST'])
    def archive_matter(matter_id):
        """Archive or reactivate a matter."""
        session = app.session
        matter = session.query(Matter).get(matter_id)
        
        if not matter:
            return jsonify({'success': False, 'message': 'Matter not found'})
        
        matter.is_active = not matter.is_active
        session.commit()
        
        return jsonify({'success': True, 'is_active': matter.is_active})
    
    @app.route('/plan')
    def plan():
        """View today's plan."""
        session = app.session
        today = date.today()
        plan = session.query(DayPlan).filter(DayPlan.date == today).first()
        
        if not plan:
            return render_template('plan.html', tasks=[])
        
        tasks = session.query(PlannedTask).filter(
            PlannedTask.day_plan_id == plan.id
        ).all()
        
        return render_template('plan.html', tasks=tasks)
    
    @app.route('/update-entry', methods=['POST'])
    def update_entry():
        """Update a work log entry."""
        data = request.json
        log_id = data.get('log_id')
        duration = data.get('duration')
        narrative = data.get('narrative')
        matter_id = data.get('matter_id')
        activity_id = data.get('activity_id')
        
        session = app.session
        log = session.query(WorkLog).get(log_id)
        
        if not log:
            return jsonify({'success': False, 'message': 'Entry not found'})
        
        if duration is not None:
            log.duration_hours = float(duration)
        
        if narrative is not None:
            log.narrative = narrative
        
        if matter_id is not None:
            log.matter_id = matter_id if matter_id else None
        
        if activity_id is not None:
            log.activity_type_id = activity_id if activity_id else None
        
        session.commit()
        
        return jsonify({'success': True, 'message': 'Entry updated'})
    
    @app.route('/delete-entry/<log_id>', methods=['POST'])
    def delete_entry(log_id):
        """Delete a work log entry."""
        session = app.session
        log = session.query(WorkLog).get(log_id)
        
        if not log:
            return jsonify({'success': False, 'message': 'Entry not found'})
        
        session.delete(log)
        session.commit()
        
        return jsonify({'success': True, 'message': 'Entry deleted'})
    
    @app.route('/export/csv')
    def export_csv():
        """Export today's work to CSV."""
        from flask import Response
        import csv
        import io
        
        session = app.session
        today = date.today()
        
        logs = session.query(WorkLog).filter(
            WorkLog.created_at >= today
        ).all()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Date', 'Matter Ref', 'Matter', 'Activity', 'Hours', 'Narrative'])
        
        # Data
        for log in logs:
            writer.writerow([
                today.isoformat(),
                log.matter.matter_ref if log.matter else '',
                log.matter.display_name if log.matter else 'General',
                log.activity_type.code if log.activity_type else 'ADMIN',
                log.duration_hours,
                log.narrative or ''
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=time_log_{today}.csv'
            }
        )
    
    # ==================== TIMER API ====================
    
    @app.route('/api/timer/status')
    def timer_status():
        """Get current timer status."""
        session = app.session
        timer = session.query(ActiveTimer).first()
        
        if not timer:
            return jsonify({
                'active': False,
                'timer': None
            })
        
        return jsonify({
            'active': True,
            'timer': {
                'id': timer.id,
                'matter_id': timer.matter_id,
                'matter_name': timer.matter.display_name if timer.matter else 'Unknown',
                'activity': timer.activity_type.label if timer.activity_type else None,
                'started_at': timer.started_at.isoformat(),
                'is_running': timer.is_active,
                'elapsed_seconds': timer.elapsed_seconds,
                'elapsed_units': timer.elapsed_units,
                'elapsed_hours': timer.elapsed_hours,
                'narrative_draft': timer.narrative_draft
            }
        })
    
    @app.route('/api/timer/start', methods=['POST'])
    def timer_start():
        """Start a new timer. Stops any existing timer first."""
        session = app.session
        data = request.json
        
        matter_id = data.get('matter_id')
        activity_id = data.get('activity_id')
        narrative = data.get('narrative', '')
        
        if not matter_id:
            return jsonify({'success': False, 'message': 'Matter is required'})
        
        # Check matter exists
        matter = session.query(Matter).get(matter_id)
        if not matter:
            return jsonify({'success': False, 'message': 'Matter not found'})
        
        # Stop any existing timer first
        existing = session.query(ActiveTimer).first()
        if existing:
            # Save existing timer as work log entry
            _save_timer_to_log(session, existing)
            session.delete(existing)
        
        # Create new timer
        timer = ActiveTimer(
            matter_id=matter_id,
            activity_type_id=activity_id if activity_id else None,
            started_at=datetime.now(),
            narrative_draft=narrative,
            is_active=True
        )
        session.add(timer)
        matter.touch()
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Timer started: {matter.display_name}',
            'timer_id': timer.id
        })
    
    @app.route('/api/timer/stop', methods=['POST'])
    def timer_stop():
        """Stop the active timer and save to work log."""
        session = app.session
        data = request.json or {}
        
        timer = session.query(ActiveTimer).first()
        if not timer:
            return jsonify({'success': False, 'message': 'No active timer'})
        
        # Get final narrative if provided
        final_narrative = data.get('narrative', timer.narrative_draft)
        
        # Save to work log
        _save_timer_to_log(session, timer, final_narrative)
        
        # Delete timer
        matter_name = timer.matter.display_name
        elapsed_units = timer.elapsed_units
        session.delete(timer)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Saved {elapsed_units} units ({elapsed_units * 0.1:.1f}h) to {matter_name}'
        })
    
    @app.route('/api/timer/pause', methods=['POST'])
    def timer_pause():
        """Pause the active timer."""
        session = app.session
        
        timer = session.query(ActiveTimer).first()
        if not timer:
            return jsonify({'success': False, 'message': 'No active timer'})
        
        if not timer.is_active:
            return jsonify({'success': False, 'message': 'Timer already paused'})
        
        # Calculate accumulated time
        running_time = (datetime.now() - timer.started_at).total_seconds()
        timer.accumulated_seconds += int(running_time)
        timer.paused_at = datetime.now()
        timer.is_active = False
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Timer paused',
            'elapsed_units': timer.elapsed_units
        })
    
    @app.route('/api/timer/resume', methods=['POST'])
    def timer_resume():
        """Resume a paused timer."""
        session = app.session
        
        timer = session.query(ActiveTimer).first()
        if not timer:
            return jsonify({'success': False, 'message': 'No active timer'})
        
        if timer.is_active:
            return jsonify({'success': False, 'message': 'Timer already running'})
        
        # Reset start time (accumulated time is preserved)
        timer.started_at = datetime.now()
        timer.paused_at = None
        timer.is_active = True
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Timer resumed'
        })
    
    @app.route('/api/timer/resume-entry/<log_id>', methods=['POST'])
    def timer_resume_entry(log_id):
        """Resume a previous work log entry (continue timer)."""
        session = app.session
        
        # Get the work log entry
        log = session.query(WorkLog).get(log_id)
        if not log:
            return jsonify({'success': False, 'message': 'Entry not found'})
        
        # Stop any existing timer
        existing = session.query(ActiveTimer).first()
        if existing:
            _save_timer_to_log(session, existing)
            session.delete(existing)
        
        # Create new timer from the log entry
        timer = ActiveTimer(
            matter_id=log.matter_id,
            activity_type_id=log.activity_type_id,
            started_at=datetime.now(),
            # Pre-load with existing time (convert hours to seconds)
            accumulated_seconds=int(log.duration_hours * 3600),
            narrative_draft=log.narrative,
            is_active=True
        )
        session.add(timer)
        
        # Delete the original log entry (it will be recreated when timer stops)
        session.delete(log)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Continuing: {timer.matter.display_name}',
            'timer_id': timer.id
        })
    
    @app.route('/api/timer/update-narrative', methods=['POST'])
    def timer_update_narrative():
        """Update the narrative of the active timer."""
        session = app.session
        data = request.json
        
        timer = session.query(ActiveTimer).first()
        if not timer:
            return jsonify({'success': False, 'message': 'No active timer'})
        
        timer.narrative_draft = data.get('narrative', '')
        session.commit()
        
        return jsonify({'success': True})
    
    
    def _save_timer_to_log(session, timer, narrative=None):
        """Helper: Save timer to work log."""
        if narrative is None:
            narrative = timer.narrative_draft
        
        # Calculate hours (minimum 0.1 = 1 unit)
        hours = max(0.1, timer.elapsed_hours)
        
        log = WorkLog(
            matter_id=timer.matter_id,
            activity_type_id=timer.activity_type_id,
            started_at=timer.created_at,
            ended_at=datetime.now(),
            duration_hours=hours,
            narrative=narrative,
            allocation_status='allocated'
        )
        session.add(log)
    
    # ========== Planning API ==========
    
    @app.route('/api/transcribe', methods=['POST'])
    def transcribe_audio():
        """Transcribe audio only (no processing) - used by Planning page."""
        import tempfile
        import os
        
        if 'audio' not in request.files:
            return jsonify({'success': False, 'transcript': '', 'message': 'No audio file'})
        
        audio_file = request.files['audio']
        
        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
                tmp_path = tmp.name
            
            audio_file.save(tmp_path)
            
            # Get or create transcriber
            transcriber = app.transcriber
            if transcriber is None:
                from ..voice.transcribe import Transcriber
                transcriber = Transcriber(
                    model_size=app.config_obj.whisper.model,
                    device=app.config_obj.whisper.device
                )
                app.transcriber = transcriber
            
            # Load vocabulary from database for better recognition
            session = app.session
            matters = session.query(Matter).filter(Matter.is_active == True).all()
            matter_vocab = []
            for m in matters:
                matter_vocab.append(m.display_name)
                if m.client:
                    matter_vocab.append(m.client)
                if m.aliases:
                    matter_vocab.extend([alias.alias for alias in m.aliases])
            
            activities = session.query(ActivityType).all()
            activity_vocab = [a.label for a in activities]
            
            # Add today's planned tasks to vocabulary
            today = date.today()
            plan = session.query(DayPlan).filter(DayPlan.date == today).first()
            task_vocab = []
            if plan:
                tasks = session.query(PlannedTask).filter(PlannedTask.day_plan_id == plan.id).all()
                for task in tasks:
                    if task.title:
                        task_vocab.append(task.title)
                        task_vocab.extend(task.title.split())
            
            full_vocab = matter_vocab + task_vocab
            transcriber.set_vocabulary(full_vocab, activity_vocab)
            
            # Transcribe
            transcript = transcriber.transcribe_file(tmp_path)
            
            # Cleanup
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return jsonify({
                'success': True,
                'transcript': transcript or ''
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'transcript': '',
                'message': str(e)
            })
    
    @app.route('/api/plan/add-task', methods=['POST'])
    def add_plan_task():
        """Add a single task to today's plan."""
        session = app.session
        data = request.json
        
        description = data.get('description', '').strip()
        matter_id = data.get('matter_id')
        activity_id = data.get('activity_id')
        
        if not description:
            return jsonify({'success': False, 'message': 'Description required'})
        
        today = date.today()
        
        # Get or create today's plan
        plan = session.query(DayPlan).filter(DayPlan.date == today).first()
        if not plan:
            plan = DayPlan(date=today)
            session.add(plan)
            session.commit()
        
        # If no matter specified, try to detect from description
        detected_matter = None
        detected_activity = None
        
        if not matter_id:
            # Try fuzzy matching
            from ..core.matcher import Matcher
            matcher = Matcher(session)
            
            match = matcher.find_matter(description)
            if match.confidence > 0.6:
                detected_matter = match.matter
                matter_id = detected_matter.id
            
            activity_match = matcher.find_activity_type(description)
            if activity_match:
                detected_activity = activity_match
                activity_id = detected_activity.id
        
        # Get next sort order
        max_order = session.query(PlannedTask).filter(
            PlannedTask.day_plan_id == plan.id
        ).count()
        
        # Create task
        task = PlannedTask(
            day_plan_id=plan.id,
            matter_id=matter_id if matter_id else None,
            activity_type_id=activity_id if activity_id else None,
            title=description,
            sort_order=max_order + 1,
            status='pending'
        )
        session.add(task)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task added',
            'task_id': task.id,
            'task_title': description,
            'matter_detected': detected_matter.display_name if detected_matter else None,
            'activity_detected': detected_activity.label if detected_activity else None
        })
    
    @app.route('/api/plan/delete-task/<task_id>', methods=['DELETE'])
    def delete_plan_task(task_id):
        """Delete a task from the plan."""
        session = app.session
        
        task = session.query(PlannedTask).filter(PlannedTask.id == task_id).first()
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        session.delete(task)
        session.commit()
        
        return jsonify({'success': True, 'message': 'Task deleted'})
    
    @app.route('/api/plan/task/<task_id>/complete', methods=['PATCH'])
    def complete_plan_task(task_id):
        """Mark a task as complete or incomplete."""
        session = app.session
        data = request.json
        
        task = session.query(PlannedTask).filter(PlannedTask.id == task_id).first()
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        completed = data.get('completed', False)
        task.status = 'done' if completed else 'pending'
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task marked as ' + ('complete' if completed else 'incomplete'),
            'status': task.status
        })
    
    @app.route('/api/plan/task/<task_id>/carry-over', methods=['POST'])
    def carry_over_task(task_id):
        """Move an incomplete task from a previous day to today's plan."""
        session = app.session
        
        # Find the original task
        original_task = session.query(PlannedTask).filter(PlannedTask.id == task_id).first()
        if not original_task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        today = date.today()
        
        # Get or create today's plan
        today_plan = session.query(DayPlan).filter(DayPlan.date == today).first()
        if not today_plan:
            today_plan = DayPlan(date=today)
            session.add(today_plan)
            session.commit()
        
        # Get next sort order for today
        max_order = session.query(PlannedTask).filter(
            PlannedTask.day_plan_id == today_plan.id
        ).count()
        
        # Create new task in today's plan
        new_task = PlannedTask(
            day_plan_id=today_plan.id,
            matter_id=original_task.matter_id,
            activity_type_id=original_task.activity_type_id,
            title=original_task.title,
            estimated_hours=original_task.estimated_hours,
            sort_order=max_order + 1,
            status='pending'
        )
        session.add(new_task)
        
        # Delete the original task
        session.delete(original_task)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task moved to today',
            'new_task_id': new_task.id
        })
    
    # =========================================================================
    # Voice Memos
    # =========================================================================
    
    @app.route('/memos')
    def memos():
        """Voice Memos page - free-form dictation for case notes."""
        from ..database.models import Memo, MemoAction
        session = app.session
        
        # Get active matters
        matters = session.query(Matter).filter(Matter.is_active == True).order_by(Matter.last_used_at.desc()).all()
        
        # Get recent memos
        recent_memos = session.query(Memo).order_by(Memo.created_at.desc()).limit(20).all()
        
        # Get pending actions (not completed)
        pending_actions = session.query(MemoAction).filter(
            MemoAction.is_completed == False
        ).order_by(MemoAction.created_at.desc()).all()
        
        return render_template('memos.html', matters=matters, memos=recent_memos, pending_actions=pending_actions)
    
    @app.route('/api/memos', methods=['POST'])
    def save_memo():
        """Save a voice memo with separate thoughts and actions."""
        from ..database.models import Memo, MemoAction
        from datetime import timedelta
        session = app.session
        
        data = request.get_json()
        matter_id = data.get('matter_id')
        thoughts = data.get('thoughts', '').strip()
        actions_text = data.get('actions', '').strip()
        duration = data.get('duration_seconds', 0)
        
        if not matter_id:
            return jsonify({'success': False, 'message': 'Matter required'})
        
        if not thoughts and not actions_text:
            return jsonify({'success': False, 'message': 'Please dictate thoughts or actions'})
        
        # Create memo
        memo = Memo(
            matter_id=matter_id,
            thoughts=thoughts or '',
            duration_seconds=duration
        )
        session.add(memo)
        session.flush()  # Get memo.id
        
        # Parse and create action items
        action_items = []
        if actions_text:
            # Split by newlines and common separators
            lines = actions_text.replace('. ', '.\n').split('\n')
            for line in lines:
                line = line.strip()
                # Remove bullet points, numbers, dashes
                line = line.lstrip('•-*0123456789.) ')
                if line and len(line) > 3:
                    action = MemoAction(
                        memo_id=memo.id,
                        matter_id=matter_id,
                        description=line,
                        due_date=date.today() + timedelta(days=1)  # Show in tomorrow's planning
                    )
                    session.add(action)
                    action_items.append(line)
        
        # Touch the matter (update recency)
        matter = session.query(Matter).filter(Matter.id == matter_id).first()
        if matter:
            matter.touch()
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Memo saved with {len(action_items)} action(s)',
            'memo_id': memo.id,
            'actions_count': len(action_items)
        })
    
    @app.route('/api/memo-actions/<action_id>', methods=['PATCH'])
    def update_memo_action(action_id):
        """Toggle action completion status."""
        from ..database.models import MemoAction
        session = app.session
        
        data = request.get_json()
        is_completed = data.get('is_completed', False)
        
        action = session.query(MemoAction).filter(MemoAction.id == action_id).first()
        if not action:
            return jsonify({'success': False, 'message': 'Action not found'})
        
        action.is_completed = is_completed
        action.completed_at = datetime.now() if is_completed else None
        session.commit()
        
        return jsonify({'success': True})
    
    @app.route('/api/memos/<matter_id>')
    def get_memos_for_matter(matter_id):
        """Get all memos for a specific matter."""
        from ..database.models import Memo
        session = app.session
        
        memos = session.query(Memo).filter(
            Memo.matter_id == matter_id
        ).order_by(Memo.created_at.desc()).all()
        
        return jsonify({
            'memos': [{
                'id': m.id,
                'thoughts': m.thoughts,
                'actions': [{'id': a.id, 'description': a.description, 'is_completed': a.is_completed} for a in m.actions],
                'created_at': m.created_at.isoformat(),
                'duration_seconds': m.duration_seconds
            } for m in memos]
        })
    
    @app.route('/api/match-matter', methods=['POST'])
    def match_matter():
        """Match spoken text to a matter - used by Voice Memos."""
        from ..core.matcher import MatterMatcher
        session = app.session
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'matter_id': None, 'matter_name': None})
        
        matcher = MatterMatcher(session, confidence_threshold=0.4)
        result = matcher.find_matter(text)
        
        if result.match:
            return jsonify({
                'matter_id': result.match.id,
                'matter_name': result.match.display_name,
                'confidence': result.confidence
            })
        else:
            return jsonify({
                'matter_id': None,
                'matter_name': None,
                'suggestions': [c[0].display_name for c in (result.candidates or [])[:3]]
            })
