"""Matter and activity matching with recency weighting."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from ..database.models import Matter, ActivityType, ActivityVocabulary


@dataclass
class MatchResult:
    """Result of a matter/activity matching operation."""
    match: Optional[Any]  # Matter or ActivityType object
    confidence: float  # 0-1
    matched_text: str = ""
    ambiguous: bool = False
    candidates: List[tuple] = None  # For ambiguous matches
    
    def __post_init__(self):
        if self.candidates is None:
            self.candidates = []


class MatterMatcher:
    """
    Matches user queries to matters using fuzzy matching with recency weighting.
    
    Key features:
    - Fuzzy alias matching (typos, abbreviations)
    - Recency weighting (recent matters score higher)
    - Ambiguity detection (top 2 scores within 90%)
    """
    
    def __init__(self, session: Session, confidence_threshold: float = 0.7):
        self.session = session
        self.confidence_threshold = confidence_threshold
    
    def find_matter(self, query: str) -> MatchResult:
        """
        Find best matching matter for a query string.
        
        Args:
            query: User's reference to a matter (e.g., "Smith", "Brown skeleton")
            
        Returns:
            MatchResult with best match or ambiguous candidates
        """
        if not query or not query.strip():
            return MatchResult(match=None, confidence=0.0)
        
        query = query.lower().strip()
        
        # Get all active matters with aliases
        matters = self.session.query(Matter).filter(Matter.is_active == True).all()
        
        if not matters:
            return MatchResult(match=None, confidence=0.0)
        
        candidates = []
        
        for matter in matters:
            # Check display name
            score = self._fuzzy_score(query, matter.display_name.lower())
            recency_weight = self._calculate_recency_weight(matter.last_used_at)
            weighted_score = score * recency_weight
            
            if weighted_score > 0:
                candidates.append((matter, weighted_score, matter.display_name))
            
            # Check all aliases
            for alias in matter.aliases:
                alias_text = alias.alias.lower()
                score = self._fuzzy_score(query, alias_text)
                weighted_score = score * recency_weight
                
                if weighted_score > 0:
                    candidates.append((matter, weighted_score, alias.alias))
        
        if not candidates:
            return MatchResult(match=None, confidence=0.0)
        
        # Sort by weighted score
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Deduplicate by matter - keep best score per matter
        seen_matters = {}
        unique_candidates = []
        for matter, score, matched_text in candidates:
            if matter.id not in seen_matters:
                seen_matters[matter.id] = True
                unique_candidates.append((matter, score, matched_text))
        
        best = unique_candidates[0]
        best_matter, best_score, matched_text = best
        
        # Normalize confidence to 0-1
        confidence = min(best_score / 100, 1.0)
        
        # Check for ambiguity (top 2 DIFFERENT matters within 90%)
        if len(unique_candidates) > 1:
            second_score = unique_candidates[1][1]
            if second_score > best_score * 0.9:
                return MatchResult(
                    match=None,
                    confidence=0.0,
                    ambiguous=True,
                    candidates=unique_candidates[:3]
                )
        
        # Check if confidence meets threshold
        if confidence < self.confidence_threshold:
            return MatchResult(
                match=None,
                confidence=confidence,
                matched_text=matched_text
            )
        
        return MatchResult(
            match=best_matter,
            confidence=confidence,
            matched_text=matched_text
        )
    
    def _fuzzy_score(self, query: str, target: str) -> float:
        """
        Calculate fuzzy matching score between query and target.
        
        Uses weighted combination of:
        - Exact substring match (highest weight)
        - Token sort ratio (handles word order)
        - Partial ratio (handles abbreviations)
        
        MINIMUM SCORE of 60 required to avoid false positives.
        """
        # Exact substring match (only for meaningful substrings)
        if len(query) >= 3 and len(target) >= 3:
            if query in target or target in query:
                return 100.0
        
        # Token sort ratio (good for reordered words)
        token_score = fuzz.token_sort_ratio(query, target)
        
        # Partial ratio (good for abbreviations)
        partial_score = fuzz.partial_ratio(query, target)
        
        # Weighted combination
        score = token_score * 0.6 + partial_score * 0.4
        
        # Require minimum score to avoid false positives like "at me" -> "matter"
        if score < 60:
            return 0.0
        
        return score
    
    def _calculate_recency_weight(self, last_used_at: Optional[datetime]) -> float:
        """
        Calculate recency weight multiplier.
        
        Reduced from original values to prevent recency from
        overriding better linguistic matches.
        
        - Used today: 1.3x
        - Used this week: 1.2x  
        - Used this month: 1.1x
        - Older: 1.0x
        """
        if not last_used_at:
            return 1.0
        
        now = datetime.now()
        delta = now - last_used_at
        
        if delta < timedelta(days=1):
            return 1.3  # Today (was 2.0)
        elif delta < timedelta(days=7):
            return 1.2  # This week (was 1.5)
        elif delta < timedelta(days=30):
            return 1.1  # This month (was 1.2)
        else:
            return 1.0  # Older


class ActivityMatcher:
    """
    Matches utterances to activity types using vocabulary phrases.
    
    Uses weighted vocabulary matching with phrase scoring.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self._vocab_cache = None
    
    def find_activity_type(self, utterance: str) -> MatchResult:
        """
        Find activity type from utterance using vocabulary matching.
        
        Args:
            utterance: User's description of work
            
        Returns:
            MatchResult with best matching activity type
        """
        if not utterance:
            return MatchResult(match=None, confidence=0.0)
        
        utterance = utterance.lower()
        
        # Load vocabulary if not cached
        if self._vocab_cache is None:
            self._load_vocabulary()
        
        # Score each activity type
        scores = {}
        matched_phrases = {}
        
        for activity_id, phrases in self._vocab_cache.items():
            score = 0
            matches = []
            
            for phrase, weight in phrases:
                if phrase in utterance:
                    score += weight * 10  # Exact phrase match
                    matches.append(phrase)
                else:
                    # Fuzzy match
                    for word in utterance.split():
                        if len(word) > 3:  # Skip short words
                            fuzzy_score = fuzz.ratio(word, phrase)
                            if fuzzy_score > 80:
                                score += weight * (fuzzy_score / 10)
                                matches.append(f"~{phrase}")
            
            if score > 0:
                scores[activity_id] = score
                matched_phrases[activity_id] = matches
        
        if not scores:
            # Default to ADMIN
            admin = self.session.query(ActivityType).filter(
                ActivityType.code == "ADMIN"
            ).first()
            return MatchResult(match=admin, confidence=0.3)
        
        # Find best match
        best_id = max(scores, key=scores.get)
        best_score = scores[best_id]
        
        # Normalize confidence
        confidence = min(best_score / 30, 1.0)
        
        activity = self.session.query(ActivityType).filter(
            ActivityType.id == best_id
        ).first()
        
        return MatchResult(
            match=activity,
            confidence=confidence,
            matched_text=", ".join(matched_phrases[best_id][:3])
        )
    
    def _load_vocabulary(self):
        """Load and cache activity vocabulary."""
        self._vocab_cache = {}
        
        vocab_entries = self.session.query(ActivityVocabulary).all()
        
        for vocab in vocab_entries:
            activity_id = vocab.activity_type_id
            if activity_id not in self._vocab_cache:
                self._vocab_cache[activity_id] = []
            
            self._vocab_cache[activity_id].append((
                vocab.phrase.lower(),
                vocab.weight
            ))
