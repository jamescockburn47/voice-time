"""Flask routes for web UI."""
from flask import render_template, request, jsonify, current_app
from datetime import date
from ..database.models import Matter, PlannedTask, WorkLog, DayPlan


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
    
    @app.route('/why')
    def why():
        """Why Voice Time? - Comparison page."""
        return render_template('why.html')
    
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
        """Main dashboard."""
        session = app.session
        
        # Get today's plan
        today = date.today()
        plan = session.query(DayPlan).filter(DayPlan.date == today).first()
        
        tasks = []
        if plan:
            tasks = session.query(PlannedTask).filter(
                PlannedTask.day_plan_id == plan.id
            ).all()
        
        # Get today's work logs
        logs = session.query(WorkLog).filter(
            WorkLog.created_at >= today
        ).all()
        
        # Calculate totals by matter
        totals = {}
        for log in logs:
            matter_name = log.matter.display_name if log.matter else "General"
            if matter_name not in totals:
                totals[matter_name] = 0.0
            totals[matter_name] += log.duration_hours
        
        return render_template(
            'index.html',
            tasks=tasks,
            logs=logs,
            totals=totals
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
        
        return jsonify({
            'success': result.success,
            'message': result.message,
            'data': result.data,
            'needs_clarification': result.needs_clarification
        })
    
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
            
            # Transcribe
            transcriber = Transcriber(
                model_size=app.config_obj.whisper.model,
                device=app.config_obj.whisper.device
            )
            transcript = transcriber.transcribe_file(tmp_path)
            
            if not transcript or not transcript.strip():
                return jsonify({
                    'success': False,
                    'message': 'No speech detected',
                    'transcript': ''
                })
            
            # Process through state machine
            result = app.day_state.process(transcript)
            
            return jsonify({
                'success': result.success,
                'message': result.message,
                'transcript': transcript,
                'data': result.data,
                'needs_clarification': result.needs_clarification
            })
            
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
    
    @app.route('/review')
    def review():
        """End-of-day review."""
        session = app.session
        today = date.today()
        
        # Get all work logs for today
        logs = session.query(WorkLog).filter(
            WorkLog.created_at >= today
        ).all()
        
        # Calculate totals by matter and activity
        summary = {}
        for log in logs:
            matter_name = log.matter.display_name if log.matter else "General"
            activity_name = log.activity_type.label if log.activity_type else "Unspecified"
            
            if matter_name not in summary:
                summary[matter_name] = {'total': 0.0, 'activities': {}}
            
            summary[matter_name]['total'] += log.duration_hours
            
            if activity_name not in summary[matter_name]['activities']:
                summary[matter_name]['activities'][activity_name] = 0.0
            
            summary[matter_name]['activities'][activity_name] += log.duration_hours
        
        return render_template('review.html', summary=summary, logs=logs)
    
    @app.route('/update-entry', methods=['POST'])
    def update_entry():
        """Update a work log entry."""
        data = request.json
        log_id = data.get('log_id')
        duration = data.get('duration')
        narrative = data.get('narrative')
        
        session = app.session
        log = session.query(WorkLog).get(log_id)
        
        if not log:
            return jsonify({'success': False, 'message': 'Entry not found'})
        
        if duration is not None:
            log.duration_hours = float(duration)
        
        if narrative is not None:
            log.narrative = narrative
        
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
