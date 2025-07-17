# Learning Opportunity Detector Design

## Overview
A streamlined component that identifies learning opportunities during free conversation to guide transitions back to structured learning.

## Core Detection System

```python
class LearningOpportunityDetector:
    def __init__(self):
        self.vocab_patterns = [
            "how do you say",
            "what's the word for",
            "I don't know how to say"
        ]
        
    async def analyze(self, context: LearningContext) -> Dict[str, Any]:
        """
        Analyze recent conversation history to identify learning opportunities.
        Returns a dictionary of opportunities and their priority.
        """
        messages = context.conversation_history[-10:]  # Look at last 5 messages
        
        opportunities = {
            "vocabulary_gaps": self._find_vocabulary_gaps(messages),
            "grammar_mistakes": self._find_grammar_mistakes(messages)
        }
        
        return {
            "opportunities": opportunities,
            "should_transition": self._should_transition(opportunities)
        }
    
    def _find_vocabulary_gaps(self, messages: List[Message]) -> List[str]:
        """Find moments where user struggles with vocabulary"""
        gaps = []
        for message in messages:
            if message.role == "user":
                # Check for vocabulary help patterns
                for pattern in self.vocab_patterns:
                    if pattern in message.content.lower():
                        gaps.append(message.content)
        return gaps
    
    def _find_grammar_mistakes(self, messages: List[Message]) -> List[str]:
        """Find grammar mistakes"""


    def _should_transition(self, opportunities: Dict) -> bool:
        """Decide if we should transition to structured learning"""
        # Simple scoring system
        score = 0
        
        # If we found vocabulary gaps, increase score
        if opportunities["vocabulary_gaps"]:
            score += 1
            
        # If we have clear topics to work with, increase score
        if opportunities["grammar_mistakes"]:
            score += 1
            
        # Transition if we have enough indicators
        return score >= 2
```

## Usage Example

```python
# In FreeConversationState
async def run(self, context: LearningContext) -> Dict:
    detector = LearningOpportunityDetector()
    analysis = await detector.analyze(context)
    
    if analysis["should_transition"]:
        # Prepare transition to structured learning
        return {
            "next_state": "add_opportunities_to_card",
            "opportunities": analysis["opportunities"]
        }
    
    return {
        "next_state": "free_conversation"
    }
```

## Key Features

1. **Simple Vocabulary Gap Detection**
   - Looks for common phrases indicating vocabulary needs
   - Easy to extend with more patterns

2. **Basic Topic Tracking**
   - Identifies main conversation themes
   - Used to find relevant study materials

3. **Learning Readiness Assessment**
   - Checks for good moments to transition
   - Avoids interrupting natural conversation flow

4. **Straightforward Decision Making**
   - Simple scoring system
   - Easy to adjust and tune