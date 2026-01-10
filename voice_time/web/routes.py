"""Flask routes for web UI."""
from flask import render_template, request, jsonify, current_app
from datetime import date
from ..database.models import Matter, PlannedTask, WorkLog, DayPlan


def register_routes(app):
    """Register all routes with the Flask app."""
    
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
        """List all active matters."""
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
