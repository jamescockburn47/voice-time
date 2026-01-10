"""
AI Assistant with strict hallucination control.

This assistant ONLY answers questions based on actual database data.
It never invents or hallucinates information about matters or time entries.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from ..database.models import Matter, WorkLog, PlannedTask, DayPlan, ActivityType, Memo, MemoAction
from .client import OllamaClient


class GroundedAssistant:
    """
    AI Assistant that only responds based on real data.
    
    Key principles:
    1. NEVER invent matters, entries, or details
    2. Always cite sources (entry IDs, dates)
    3. Say "I don't have that information" when data is unavailable
    4. Only make claims that can be verified from the database
    """
    
    def __init__(self, llm_client: OllamaClient, session: Session):
        self.llm = llm_client
        self.session = session
    
    def _get_context(self, query: str) -> Dict[str, Any]:
        """
        Gather relevant context from database based on query.
        Returns structured data that grounds the LLM response.
        """
        context = {
            'today': str(date.today()),
            'current_time': datetime.now().strftime('%H:%M'),
        }
        
        # Get all active matters
        matters = self.session.query(Matter).filter(Matter.is_active == True).all()
        context['matters'] = [
            {
                'id': m.id,
                'name': m.display_name,
                'client': m.client,
                'ref': m.matter_ref,
                'use_count': m.use_count,
                'last_used': str(m.last_used_at.date()) if m.last_used_at else None
            }
            for m in matters
        ]
        
        # Get this week's entries
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_logs = self.session.query(WorkLog).filter(
            WorkLog.created_at >= week_start
        ).all()
        
        context['week_entries'] = [
            {
                'id': log.id[:8],  # Short ID for reference
                'date': str(log.created_at.date()) if log.created_at else str(log.started_at.date()) if log.started_at else None,
                'matter': log.matter.display_name if log.matter else 'General',
                'activity': log.activity_type.label if log.activity_type else 'Unknown',
                'hours': log.duration_hours,
                'narrative': log.narrative[:100] if log.narrative else ''
            }
            for log in week_logs
        ]
        
        # Calculate totals
        context['week_total_hours'] = sum(e['hours'] for e in context['week_entries'])
        
        # Matter totals for the week
        matter_totals = {}
        for entry in context['week_entries']:
            matter = entry['matter']
            if matter not in matter_totals:
                matter_totals[matter] = 0
            matter_totals[matter] += entry['hours']
        context['week_by_matter'] = matter_totals
        
        # Today's entries
        today = date.today()
        today_logs = [e for e in context['week_entries'] if e['date'] == str(today)]
        context['today_entries'] = today_logs
        context['today_total_hours'] = sum(e['hours'] for e in today_logs)
        
        # Today's plan
        plan = self.session.query(DayPlan).filter(DayPlan.date == today).first()
        if plan:
            tasks = self.session.query(PlannedTask).filter(
                PlannedTask.day_plan_id == plan.id
            ).all()
            context['today_plan'] = [
                {
                    'task': t.title,
                    'matter': t.matter.display_name if t.matter else 'General',
                    'status': t.status,
                    'estimated_hours': t.estimated_hours
                }
                for t in tasks
            ]
        else:
            context['today_plan'] = []
        
        # Voice Memos (recent)
        recent_memos = self.session.query(Memo).order_by(Memo.created_at.desc()).limit(20).all()
        context['memos'] = [
            {
                'id': m.id[:8],
                'date': str(m.created_at.date()) if m.created_at else None,
                'matter': m.matter.display_name if m.matter else 'General',
                'thoughts': m.thoughts[:150] if m.thoughts else '',
                'actions_count': len(m.actions) if m.actions else 0
            }
            for m in recent_memos
        ]
        
        # Pending Actions from memos
        pending_actions = self.session.query(MemoAction).filter(
            MemoAction.is_completed == False
        ).order_by(MemoAction.created_at.desc()).all()
        context['pending_actions'] = [
            {
                'id': a.id[:8],
                'matter': a.matter.display_name if a.matter else 'General',
                'description': a.description,
                'due_date': str(a.due_date) if a.due_date else None,
                'created': str(a.created_at.date()) if a.created_at else None
            }
            for a in pending_actions
        ]
        
        # Completed actions this week
        completed_actions = self.session.query(MemoAction).filter(
            MemoAction.is_completed == True,
            MemoAction.completed_at >= week_start
        ).all()
        context['completed_actions_count'] = len(completed_actions)
        
        return context
    
    def _build_grounded_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build a prompt that strictly grounds the LLM in real data."""
        
        prompt = f"""You are a legal time tracking assistant. You MUST follow these rules:

CRITICAL RULES:
1. ONLY use information from the DATA section below. NEVER invent or assume data.
2. If asked about something not in the data, say "I don't have that information in your records."
3. When citing numbers, reference the source (e.g., "Entry abc123 on Jan 10").
4. Be helpful but NEVER hallucinate details about matters, clients, or time entries.
5. Keep responses concise and professional.

TODAY: {context['today']}
CURRENT TIME: {context['current_time']}

=== YOUR MATTERS ({len(context['matters'])} active) ===
"""
        for m in context['matters'][:15]:  # Limit to prevent context overflow
            prompt += f"- {m['name']} (Client: {m['client']}, Ref: {m['ref']}, Used {m['use_count']}x)\n"
        
        prompt += f"""
=== THIS WEEK'S TIME ENTRIES ({len(context['week_entries'])} entries, {context['week_total_hours']:.1f}h total) ===
"""
        for entry in context['week_entries'][:20]:  # Limit entries
            prompt += f"- [{entry['id']}] {entry['date']}: {entry['matter']} - {entry['activity']} ({entry['hours']:.1f}h)\n"
        
        prompt += f"""
=== WEEK TOTALS BY MATTER ===
"""
        for matter, hours in context['week_by_matter'].items():
            prompt += f"- {matter}: {hours:.1f}h\n"
        
        prompt += f"""
=== TODAY'S ENTRIES ({len(context['today_entries'])} entries, {context['today_total_hours']:.1f}h) ===
"""
        for entry in context['today_entries']:
            prompt += f"- [{entry['id']}] {entry['matter']} - {entry['activity']} ({entry['hours']:.1f}h): {entry['narrative'][:50]}...\n"
        
        if context['today_plan']:
            prompt += f"""
=== TODAY'S PLAN ===
"""
            for task in context['today_plan']:
                prompt += f"- {task['task']} ({task['matter']}) - Status: {task['status']}\n"
        
        # Voice Memos
        if context.get('memos'):
            prompt += f"""
=== RECENT VOICE MEMOS ({len(context['memos'])} memos) ===
"""
            for memo in context['memos'][:10]:
                prompt += f"- [{memo['id']}] {memo['date']}: {memo['matter']} - {memo['thoughts'][:80]}... ({memo['actions_count']} actions)\n"
        
        # Pending Actions
        if context.get('pending_actions'):
            prompt += f"""
=== PENDING ACTION ITEMS ({len(context['pending_actions'])} pending) ===
"""
            for action in context['pending_actions'][:15]:
                prompt += f"- [{action['id']}] {action['matter']}: {action['description']} (due: {action['due_date']})\n"
        
        if context.get('completed_actions_count', 0) > 0:
            prompt += f"\nCompleted actions this week: {context['completed_actions_count']}\n"
        
        prompt += f"""
=== USER QUESTION ===
{query}

Remember: ONLY answer based on the data above. If the information isn't there, say so clearly.
"""
        return prompt
    
    def chat(self, query: str) -> Dict[str, Any]:
        """
        Answer a question using only grounded data.
        
        Returns:
            Dict with 'response', 'sources', and 'confidence'
        """
        # Get relevant context
        context = self._get_context(query)
        
        # Build grounded prompt
        prompt = self._build_grounded_prompt(query, context)
        
        # Get LLM response
        try:
            result = self.llm.generate(prompt, json_mode=False, temperature=0.3)
            response = result.get('text', '').strip()
            
            return {
                'success': True,
                'response': response,
                'context_used': {
                    'matters_count': len(context['matters']),
                    'week_entries_count': len(context['week_entries']),
                    'week_total_hours': context['week_total_hours'],
                    'today_entries_count': len(context['today_entries']),
                    'today_total_hours': context['today_total_hours'],
                    'memos_count': len(context.get('memos', [])),
                    'pending_actions_count': len(context.get('pending_actions', []))
                }
            }
        except Exception as e:
            return {
                'success': False,
                'response': f'Error: {str(e)}',
                'context_used': {}
            }
    
    def generate_day_summary(self) -> Dict[str, Any]:
        """Generate a professional summary of today's work."""
        context = self._get_context("")
        
        if not context['today_entries']:
            return {
                'success': True,
                'summary': "No time entries recorded today.",
                'hours': 0
            }
        
        prompt = f"""Generate a brief professional summary of today's work for internal records.

TODAY'S ENTRIES:
"""
        for entry in context['today_entries']:
            prompt += f"- {entry['matter']}: {entry['activity']} ({entry['hours']:.1f}h) - {entry['narrative']}\n"
        
        prompt += f"""
TOTAL: {context['today_total_hours']:.1f} hours

Write a 2-3 sentence summary suitable for a daily work log. Be factual and professional.
Only mention work that appears in the entries above. Do not add details not present."""
        
        try:
            result = self.llm.generate(prompt, json_mode=False, temperature=0.3)
            return {
                'success': True,
                'summary': result.get('text', '').strip(),
                'hours': context['today_total_hours'],
                'entries_count': len(context['today_entries'])
            }
        except Exception as e:
            return {
                'success': False,
                'summary': f'Error generating summary: {str(e)}',
                'hours': context['today_total_hours']
            }
    
    def generate_client_update(self, matter_name: str) -> Dict[str, Any]:
        """Generate a draft client update email for a specific matter."""
        context = self._get_context("")
        
        # Find entries for this matter
        matter_entries = [
            e for e in context['week_entries']
            if matter_name.lower() in e['matter'].lower()
        ]
        
        if not matter_entries:
            return {
                'success': False,
                'email': f"No time entries found for '{matter_name}' this week.",
                'matter': matter_name
            }
        
        # Find the matter details
        matter_info = next(
            (m for m in context['matters'] if matter_name.lower() in m['name'].lower()),
            None
        )
        
        total_hours = sum(e['hours'] for e in matter_entries)
        
        prompt = f"""Draft a brief professional email update to a client about work done on their matter.

MATTER: {matter_info['name'] if matter_info else matter_name}
CLIENT: {matter_info['client'] if matter_info else 'Client'}

THIS WEEK'S WORK:
"""
        for entry in matter_entries:
            prompt += f"- {entry['date']}: {entry['activity']} ({entry['hours']:.1f}h) - {entry['narrative']}\n"
        
        prompt += f"""
TOTAL THIS WEEK: {total_hours:.1f} hours

Write a professional, concise email update. Include:
1. Brief greeting
2. Summary of work completed (only what's listed above)
3. Next steps if obvious from the entries
4. Professional sign-off

Do NOT invent work not listed above. Do NOT add billing details or fees."""
        
        try:
            result = self.llm.generate(prompt, json_mode=False, temperature=0.4)
            return {
                'success': True,
                'email': result.get('text', '').strip(),
                'matter': matter_info['name'] if matter_info else matter_name,
                'total_hours': total_hours,
                'entries_count': len(matter_entries)
            }
        except Exception as e:
            return {
                'success': False,
                'email': f'Error: {str(e)}',
                'matter': matter_name
            }
    
    def suggest_next_task(self) -> Dict[str, Any]:
        """Suggest what to work on next based on plan and patterns."""
        context = self._get_context("")
        
        prompt = f"""Based on the data below, suggest what the user should work on next.

TODAY'S PLAN:
"""
        if context['today_plan']:
            for task in context['today_plan']:
                prompt += f"- {task['task']} ({task['matter']}) - Status: {task['status']}\n"
        else:
            prompt += "No plan set for today.\n"
        
        prompt += f"""
ALREADY DONE TODAY ({context['today_total_hours']:.1f}h):
"""
        for entry in context['today_entries']:
            prompt += f"- {entry['matter']}: {entry['hours']:.1f}h\n"
        
        prompt += f"""
CURRENT TIME: {context['current_time']}

Suggest ONE task to focus on next. Be specific and reference the plan if there is one.
If all planned tasks are done, suggest reviewing entries or planning tomorrow."""
        
        try:
            result = self.llm.generate(prompt, json_mode=False, temperature=0.5)
            return {
                'success': True,
                'suggestion': result.get('text', '').strip(),
                'based_on': 'plan' if context['today_plan'] else 'patterns'
            }
        except Exception as e:
            return {
                'success': False,
                'suggestion': f'Error: {str(e)}'
            }
    
    def analyze_week(self) -> Dict[str, Any]:
        """Analyze the week's time distribution and patterns."""
        context = self._get_context("")
        
        if not context['week_entries']:
            return {
                'success': True,
                'analysis': "No time entries recorded this week yet.",
                'total_hours': 0
            }
        
        prompt = f"""Analyze this week's time tracking data and provide insights.

WEEK TOTALS BY MATTER:
"""
        for matter, hours in context['week_by_matter'].items():
            prompt += f"- {matter}: {hours:.1f}h\n"
        
        prompt += f"""
TOTAL: {context['week_total_hours']:.1f} hours across {len(context['week_entries'])} entries

Provide a brief analysis (3-4 sentences) covering:
1. Where most time was spent
2. Any notable patterns
3. Suggestion for the remaining week (if relevant)

Only reference matters that appear in the data above."""
        
        try:
            result = self.llm.generate(prompt, json_mode=False, temperature=0.4)
            return {
                'success': True,
                'analysis': result.get('text', '').strip(),
                'total_hours': context['week_total_hours'],
                'by_matter': context['week_by_matter']
            }
        except Exception as e:
            return {
                'success': False,
                'analysis': f'Error: {str(e)}'
            }
