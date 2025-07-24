from typing import Annotated, Dict, Any, List, Optional, cast

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent, ToolNode, tools_condition
from langgraph.types import Command, interrupt
from langchain_core.language_models import BaseLLM
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_core.language_models import BaseChatModel  # Change this import
from langchain_core.runnables import RunnableConfig


from anki.anki import (
    add_anki_note,
    _check_anki_connection_internal,
    check_anki_connection,
    create_anki_deck,
    get_note_by_id,
    search_notes_by_content,
    find_cards_to_talk_about,
    answer_card,
    answer_multiple_cards
)

class KotoriState(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]
    
    round_start_msg_idx: int  # Index of the message where the current round of conversation started
    
    learning_goals: str
    
    next: str # The next state to transition to
    
    active_cards: str
    
    assessment_history: List[str]
    
    calling_node: str  # Track which node called the tools
    
    counter: int
    
class KotoriConfig(TypedDict):
    language: str # possible values: "english" and "japanese"
    deck_name: Optional[str] # Name of the Anki deck to read, Kotori will always add cards to 'Kotori' deck
    temperature: Optional[float]  # Temperature for LLM responses, default is 0.1
    
    
class KotoriBot:
    """Language learning bot that manages conversation flow and learning state."""
    def __init__(self, llm: BaseChatModel, config: KotoriConfig):
        # Initialize the state graph with the defined state schema
        self.graph = StateGraph(state_schema=KotoriState)
        
        # Apply temperature configuration to the LLM
        self.llm = llm
        self.set_config(config)
        
        # Define tools for Anki operations
        self.tools = [
            add_anki_note,
            check_anki_connection,
            get_note_by_id,
            search_notes_by_content,
            find_cards_to_talk_about,
            answer_card,
            answer_multiple_cards
        ]
        
        # Create tool node for handling tool calls
        self.tool_node = ToolNode(self.tools)
        
        # Define the states and their transitions
        self._setup_nodes()
        self._setup_edges()
        
        # Compile the graph with checkpointer for proper state management
        from langgraph.checkpoint.memory import MemorySaver
        memory = MemorySaver()
        self.app = self.graph.compile(checkpointer=memory)
        
        # Note: With interrupts, user input is handled within the nodes themselves
    
    def _setup_nodes(self):
        """Set up all the nodes in the state graph."""
        # Nodes that use interrupts for user input
        self.graph.add_node("greeting", self._greeting_node)
        self.graph.add_node("topic_selection_prompt", self._topic_selection_prompt_node)
        self.graph.add_node("conversation", self._conversation_node)
        self.graph.add_node("free_conversation", self._free_conversation_node)
        
        # Internal processing nodes (no user input needed)
        self.graph.add_node("retrieve_cards", self._retrieve_cards_node)
        self.graph.add_node("assessment", self._assessment_node)
        self.graph.add_node("topic_selection", self._topic_selection_node)
        self.graph.add_node("free_conversation_eval", self._free_conversation_eval_node)
        self.graph.add_node("card_answer", self._card_answer_node)
        
        # Add the tool node for handling tool calls
        self.graph.add_node("tools", self.tool_node)
        
    def _setup_edges(self):
        """Set up the edges and conditional routing between nodes."""
        # Start with greeting
        self.graph.add_edge(START, "greeting")
        
        # Add conditional edges based on the 'next' field in state
        self.graph.add_conditional_edges(
            "greeting",
            self._route_next,
            ["topic_selection_prompt", "greeting", END]
        )
        
        self.graph.add_conditional_edges(
            "topic_selection_prompt",
            self._route_next,
            ["topic_selection"]
        )
        
        self.graph.add_conditional_edges(
            "topic_selection",
            self._route_next,
            ["conversation", "retrieve_cards"]
        )
        
        self.graph.add_conditional_edges(
            "retrieve_cards",
            self._route_next,
            ["conversation", "free_conversation"]
        )
        
        # Conversation node can also use tools
        self.graph.add_conditional_edges(
            "conversation",
            self._route_next,
            ["assessment", "conversation", "topic_selection_prompt", "tools"]
        )
        
        self.graph.add_conditional_edges(
            "free_conversation",
            self._route_next,
            ["topic_selection_prompt", "free_conversation", "free_conversation_eval", "tools"]
        )
        
        # Assessment node can also use tools
        self.graph.add_conditional_edges(
            "assessment",
            self._route_next,
            ["card_answer", "conversation"]
        )
        
        # Card answer node can either use tools or go to next state
        self.graph.add_conditional_edges(
            "card_answer",
            self._route_next,
            ["tools", "topic_selection_prompt"]
        )
        
        # After tools are executed, we need to route back to the calling node
        # We'll use a custom routing function to determine where to return
        self.graph.add_conditional_edges(
            "tools",
            self._route_after_tools,
            ["card_answer", "conversation", "topic_selection", "free_conversation"]
        )
        
        # Internal nodes route automatically
        self.graph.add_conditional_edges(
            "free_conversation_eval",
            self._route_next,
            ["assessment", "topic_selection_prompt", "free_conversation", END]
        )
    
    def _route_next(self, state: KotoriState) -> str:
        """Route to the next state based on the 'next' field."""
        toolNext = tools_condition(state["messages"])
        if toolNext == "tools":
            return "tools"
        
        return state.get("next", END)
    
    def _route_after_tools(self, state: KotoriState) -> str:
        """Route back to the appropriate node after tools execution."""
        # Check which node called the tools by looking at the context
        # You can implement different strategies here:
        
        # Strategy 1: Use a field in state to track the calling node
        calling_node = state.get("calling_node", "topic_selection_prompt")
        
        # Validate that the calling node is a valid destination
        valid_destinations = ["card_answer", "conversation", "assessment", "topic_selection", "free_conversation"]
        
        if calling_node in valid_destinations:
            return calling_node
        else:
            # Fallback to topic_selection if invalid calling node
            return "topic_selection_prompt"
    
    def _get_temperature(self) -> float:
        """Return the temperature for LLM responses."""
        temperature = self.config.get('temperature', 0.1)
        if temperature is None:
            return 0.1  # Default temperature if not set
        
        return temperature
    
    def _get_configured_llm(self):
        """Return the LLM with temperature configuration applied."""
        # Use bind to set temperature - this is the recommended approach for most LLMs
        try:
            return self.llm.bind(temperature=self._get_temperature())
        except Exception as e:
            print(f"Warning: Could not configure temperature: {e}")
            # If temperature configuration is not supported, return the original LLM
            return self.llm
    
    def set_temperature(self, temperature: float):
        """Update the temperature configuration."""
        if temperature < 0 or temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        self.config['temperature'] = temperature
    
    def get_current_temperature(self) -> float:
        """Get the current temperature setting."""
        return self._get_temperature()

    def set_config(self, config:KotoriConfig):
        """Update the configuration for the bot."""
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")
        
        # Validate required fields
        if 'language' not in config or config['language'] not in ['english', 'japanese']:
            raise ValueError("Language must be 'english' or 'japanese'")
        
        if 'deck_name' in config and not isinstance(config['deck_name'], str):
            raise ValueError("Deck name must be a string")
        
        if 'temperature' in config:
            if not isinstance(config['temperature'], (float, int)):
                raise ValueError("Temperature must be a number")
            if config['temperature'] < 0 or config['temperature'] > 2:
                raise ValueError("Temperature must be between 0 and 2")
        
        self.config = config
    
    # Node implementations
    async def _greeting_node(self, state: KotoriState) -> KotoriState:
        """Handle initial greeting and goal setting."""
        messages = state.get("messages", [])
        
        if len(messages) == 0:
            # First interaction - generate greeting and get user input
            language = self.config.get('language', 'english')
            if language == "english":
                greeting_prompt = f"Hello! I'm Kotori, your {language} learning assistant. What is your level and what would you like to learn today?"
            elif language == "japanese":
                greeting_prompt = "こんにちは！私はコトリ、あなたの日本語学習アシスタントです。あなたのレベルと、今日学びたいことは何ですか？"
            else:
                greeting_prompt = "Language not supported. Please choose English or Japanese."
                state["next"] = END
                return state
            
            # Use interrupt to get user input
            user_input = interrupt(greeting_prompt)
            
            # Add both assistant greeting and user response to messages
            greeting_msg = AIMessage(content=greeting_prompt)
            state["messages"].append(greeting_msg)
            user_msg = HumanMessage(content=user_input)
            state["messages"].append(user_msg)
            
            # Process user's learning goals
            state["learning_goals"] = user_input
            state["next"] = "topic_selection_prompt"  # Move to topic selection
        else:
            # This shouldn't happen in normal flow, but handle gracefully
            state["next"] = "topic_selection_prompt"
        
        return state
    
    def _get_recent_messages(self, state, count: int = 6) -> List[BaseMessage]:
        """Get the last 'count' messages from the conversation history."""
        
        round_start_idx = state.get("round_start_msg_idx", 0)
        msgs = state.get("messages", [])
        
        if not msgs or round_start_idx >= len(msgs):
            return []
        
        # Get messages from the start of the round to the end
        round_messages = msgs[round_start_idx:]
        if len(round_messages) < count:
            return round_messages
        
        # Return the last 'count' messages from the round
        return round_messages[-count:]
    
    async def _topic_selection_prompt_node(self, state: KotoriState) -> KotoriState:
        """Generate assistant message for topic selection and get user input."""
        language = self.config.get('language', 'english')
        learning_goals = state.get("learning_goals", "general")
        system_prompt = f'''You are Kotori, a friendly and helpful language learning assistant specialized in teaching {language}.
Based on the conversation history and the user's learning goals {learning_goals}, ask the user if they have a specific topic they would like to discuss.
Keep your message encouraging, concise, and end with a clear question about if they want to discuss a specific topic.
Respond naturally in {language} if the user's level seems intermediate or above, otherwise use simpler {language}.
        '''
        system_prompt = system_prompt.format(language=language, learning_goals=learning_goals)
        
        # Get recent messages to provide context
        user_messages_history = self._get_recent_messages(state, count=10)
        
        configured_llm = self._get_configured_llm()
        topic_msg = await configured_llm.ainvoke([
            SystemMessage(content=system_prompt)
        ] + user_messages_history)
        
        # Extract content from the response message
        content = getattr(topic_msg, 'content', str(topic_msg))
        
        # Use interrupt to get user input
        user_input = interrupt(content)
        
        # Add both assistant message and user response to messages
        state["messages"].append(AIMessage(content=content))
        user_msg = HumanMessage(content=user_input)
        state["messages"].append(user_msg)
        
        state["next"] = "topic_selection"
        
        return state
        
    async def _topic_selection_node(self, state: KotoriState) -> KotoriState:
        """Internal node - select appropriate learning topic based on goals."""
        # This is an internal processing node - no assistant message

        # System prompt to determine if user has a specific topic they want to discuss
        system_prompt = f"""
You are a task manager.  Given a user's recent message history and descriptions of available routes, analyze and determine the next route.
Select the appropriate route based on the user's intent and available options. Respond only with the chosen route's number.
Routes:
1. FREE_CONVERSATION: The user has topics they want to discuss freely.
2. GUIDED_CONVERSATION: The user has no specific topics, but you can find Anki cards to discuss.
Examples:
- "I want to talk about cooking" -> 1
- "Let's discuss Japanese culture" -> 1
- "I want to do free talk" -> 1
- "No, I don't have anything specific" -> 2
- "What should we talk about?" -> 2
- "I'm not sure" -> 2
- "I want to review anki cards" -> 2
"""
        user_history = self._get_recent_messages(state, count=6)
        
        user_input = str(
            "recent messages: {{{" + " ".join([f"[{msg.__class__.__name__}] {str(msg.content)}" for msg in user_history]) + "}}} Remember you must only output a number which corresponds to a route. "
            "given above based on your understanding of the recent messages and the user's intent."
        )
        
        topic_response = await self._get_configured_llm().ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input)
        ])
    
        topic_decision = str(topic_response).strip()
        
        state = self._reset_learning_states(state)
        if "1" in topic_decision:
            # User has a topic, transition to free conversation
            state['next'] = 'free_conversation'
        else:
            # User doesn't have a topic, go to retrieve cards
            state['next'] = 'retrieve_cards'
    
        return state
    
    async def _retrieve_cards_node(self, state: KotoriState) -> KotoriState:
        try:
            # Try to find cards from Anki to discuss
            deck_name = self.config.get('deck_name', 'Kotori')  # Default deck name
            cards_result = await find_cards_to_talk_about.ainvoke({"deck_name": deck_name, "limit": 1}) # only give one card at a time

            # Parse the result to check if cards were found
            if "Error" in cards_result or "No cards found" in cards_result:
                # No cards found, transition to free conversation
                state['next'] = 'free_conversation'
                    
            else:
                # Cards found, transition to structured conversation
                state['next'] = 'conversation'
                # Note: In a real implementation, you'd parse the cards_result 
                # and store the card data in state['active_cards']
                state['active_cards'] = cards_result
        
        except Exception as e:
            # Error accessing Anki, fallback to free conversation
            state['next'] = 'free_conversation'
        
        return state
        
    def _reset_learning_states(self, state: KotoriState) -> KotoriState:
        """Reset learning-related states to prepare for a new topic."""
        state['active_cards'] = ''
        state['learning_goals'] = ''
        state['counter'] = 0
        
        msg_len = len(state['messages'])
        
        state['round_start_msg_idx'] = msg_len  # Track where the round started
        return state
    
    async def _conversation_node(self, state: KotoriState) -> KotoriState:
        """Handle structured conversation with learning cards."""
        # Generate assistant message for conversation
        active_cards = state.get("active_cards", "general topics")
        language = self.config.get('language', 'english')
        learning_goal = state.get('learning_goals', 'general conversation')
        
        state["calling_node"] = "conversation"  # Track which node called the tools
        
        # Create a simple prompt for the LLM
        system_message = SystemMessage(content=f"""
You are Kotori, a helpful {language} language learning assistant.
ACTIVE CARD: {active_cards}
User level and learning goal: {learning_goal}
CORE APPROACH:
Build the entire conversation around the active card's vocabulary/concept.

STRATEGY:
1. **Natural Integration**: Introduce the vocabulary organically in your first response within a relatable context
2. **Deep Practice**: Use the vocabulary 1-2 times per response, ask questions that encourage user practice
3. **Level-Appropriate**: For beginners: Use simple sentences, provide clear examples, explain meaning if needed; For intermediate users, use natural {language} and encourage complex usage; For advanced users, challenge them with nuanced uses, idioms, or cultural contexts
4. **Reinforcement**: Acknowledge correct usage positively, provide gentle corrections when needed
5. **Conversation Flow**: Keep focus on target vocabulary, guide back if conversation drifts

TOOLS:
- Use add_anki_note for new vocabulary the user struggles with (not from active card)

RESPONSE STYLE:
- Conversational and encouraging
- 2-3 vocabulary practice opportunities per turn
- End with questions using target vocabulary
- Max 2-3 questions at once
- Clear language appropriate for user level

GOAL: Provide focused, deep practice of the single vocabulary item for true mastery.                               
""")
        
        # Bind tools and temperature together
        llm_with_tools = self.llm.bind_tools([add_anki_note, check_anki_connection], temperature=self._get_temperature())
        
        recent_messages = self._get_recent_messages(state, count=10)
        
        response = await llm_with_tools.ainvoke([
            system_message]+ recent_messages)
        state["messages"].append(response)
        
        if tools_condition(state["messages"]) == "tools":
            # If tools were called, route to the tool node
            state["next"] = "tools"
            return state
        
        # Handle both string and message responses
        content = getattr(response, 'content', str(response))
        
        # Use interrupt to get user input
        user_input = interrupt(content)
        
        # Add both assistant message and user response to messages
        user_msg = HumanMessage(content=user_input)
        state["messages"].append(user_msg)
        
        state["next"] = "assessment"  # Move to assessment
        
        return state

    async def _do_card_assessment(self, state: KotoriState, current_conversation_count: int) -> KotoriState:
        # this is not a node, but a helper function to assess user's understanding of the active card
        """Assess user's understanding of the active card."""
        active_cards = state.get("active_cards", "")
        language = self.config.get('language', 'english')
        if current_conversation_count > 0 and active_cards != "":
            user_history = self._get_recent_messages(state, count=current_conversation_count)
            system_prompt = f"""
You are assessing a language learner's mastery of vocabulary and grammar in {language} of an active card based on user recent messages.

ACTIVE CARD (either Grammar or Vocabulary): {active_cards}

ASSESSMENT CRITERIA (1-5 scale for each):

1. MEANING UNDERSTANDING (1-5): 
   - Vocabulary: Do they grasp the word's core meaning, nuances, and different senses?
   - Grammar: Do they understand what the grammatical structure conveys or expresses?

2. USAGE ACCURACY (1-5):
   - Vocabulary: Do they use the word with correct form, spelling, and grammatical context?
   - Grammar: Do they apply the structure with correct form, word order, and morphology?

3. NATURALNESS (1-5):
   - Vocabulary: Do they use the word in natural collocations, appropriate register, and fitting contexts?
   - Grammar: Do they use the structure fluently, in appropriate situations, and with natural timing?

SCORING GUIDELINES:
- 5: Excellent mastery - native-like understanding and usage
- 4: Good competency - minor gaps but generally accurate and natural
- 3: Fair grasp - basic understanding with some errors or awkwardness
- 2: Limited proficiency - significant gaps in understanding or usage
- 1: Minimal competency - major difficulties across all areas

ASSESSMENT FORMAT:
== Assessment for [[card front]]
MEANING_UNDERSTANDING: [score 1-5] - [specific evidence from user's messages briefly summarized]
USAGE_ACCURACY: [score 1-5] - [examples of correct/incorrect usage briefly summarized]
NATURALNESS: [score 1-5] - [assessment of natural vs. awkward usage]

OVERALL_MASTERY: [score 1-5] - [brief summary]

NEXT_STEPS: [1-2 specific, actionable recommendations]
"""
            user_input = str(
            "recent messages: {{{" + " ".join([f"[{msg.__class__.__name__}] {str(msg.content)}" for msg in user_history]) + "}}} Analyze the user's recent messages for concrete evidence of these three aspects for the active card. Respond following the ASSESSMENT FORMAT."
            )
            
            assessment_response = await self._get_configured_llm().ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ])

            current_assessment = str(assessment_response.content)
            assessment_history = state.get("assessment_history", [])
            assessment_history.append(current_assessment)
            state["assessment_history"] = assessment_history
        
        return state

    async def _assessment_node(self, state: KotoriState) -> KotoriState:
        """Assess user's understanding on the active card."""
        
        # Get the latest user message
        last_user_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_user_message = msg
                break
        
        if not last_user_message:
            # No user message to assess, continue conversation
            state["next"] = "conversation"
            return state
        
        language = self.config.get('language', 'english')
        active_cards = state.get("active_cards", "")
        
        # will get the recent messages in this round
        user_history = self._get_recent_messages(state, count=10)
        round_start_msg_idx = state.get("round_start_msg_idx", 0)
        msgs = state.get("messages", [])
        current_conversation_count = len(msgs) - round_start_msg_idx

        route_next_system_prompt = f"""
You are a task manager for {language} language learning assessment. Given a user's recent message history and their interaction with active vocabulary cards, analyze and determine the next route.
Select the appropriate route based on the user's learning progress and intent. Respond only with the chosen route's number.
ACTIVE CARD: {active_cards}
CURRENT ROUND MESSAGE COUNT: {current_conversation_count}
Routes:
1. FREE_CONVERSATION: The user expresses intent to do free talk or general conversation unrelated to the active card.
2. RETRIEVE_CARDS: The user has demonstrated sufficient understanding of the active card OR the conversation has exceeded 10 messages in the current round and the user is not asking questions / help / clarification OR the user expresses they want to change to a different vocabulary word.
3. CONVERSATION: The user needs more practice with the current active card vocabulary OR the user demonstrates intent to continue the topic by asking for help or clarification about the active card vocabulary.

KEY INSIGHT: Adding the active card to Anki means they want to study it more → Route 3

Examples:
FREE_CONVERSATION (Route 1):
- "Can we talk about something else?" → 1
- "I want to do free conversation now" → 1
- "Let's chat about random topics" → 1
- "I'm bored with this vocabulary" → 1

RETRIEVE_CARDS (Route 2):
- User correctly uses active card vocabulary multiple times → 2
- User shows mastery of current vocabulary → 2
- CURRENT ROUND MESSAGE COUNT has 10+ messages, and user is not asking more questions or help → 2
- "Can we talk about a different word?" → 2
- "I understand this word well now" → 2
- "Let's try new vocabulary" → 2

CONVERSATION (Route 3):
- User asks clarifying questions about active vocabulary → 3
- User struggles with active card concepts → 3
- User partially understands but needs more practice → 3
- "What does this word mean again?" → 3
- "Can you give me another example?" → 3
- "Put the word 'tree' into anki." → 3
- "How do I use this word in a sentence?" → 3
- User attempts to use active vocabulary but makes errors → 3
"""

        user_input = str(
            "recent messages: {{{" + " ".join([f"[{msg.__class__.__name__}] {str(msg.content)}" for msg in user_history]) + "}}} Remember you must only output a number which corresponds to a route. "
            "given above based on your understanding of the recent messages and the user's intent."
        )


        topic_response = await self._get_configured_llm().ainvoke([
            SystemMessage(content=route_next_system_prompt),
            HumanMessage(content=user_input)
        ])
    
        topic_decision = str(topic_response).strip()
        
        if "1" in topic_decision or "2" in topic_decision:
            if current_conversation_count > 0:
                state = await self._do_card_assessment(state, current_conversation_count)
            
        if "1" in topic_decision:
            state = self._reset_learning_states(state)
            state['next'] = 'free_conversation'
        elif "2" in topic_decision:
            # User has demonstrated understanding or wants to change vocabulary
            state = self._reset_learning_states(state)
            state['next'] = 'retrieve_cards'
        else: # Copilot might not know what to do, or it chooses 3, let's continue conversation
            state['next'] = 'conversation'
            
        return state
    
    async def _card_answer_node(self, state: KotoriState) -> KotoriState:
        """Handle answering a specific card using tools."""
        
        # First time in this node - decide what to do based on assessment
        assessment_history = state.get("assessment_history", "")
        active_cards = state.get("active_cards", "")
        
        # Set the calling node for proper routing after tools
        state["calling_node"] = "card_answer"
        
        # Create a prompt for the LLM to decide which tools to use
        system_prompt = f"""
        You are helping a language learner practice with Anki cards. 
        
        Current active cards: {active_cards}
        Assessment history: {assessment_history}
        
        Based on the assessment history and the cards they're working with, you should:
        Use answer_card or answer_multiple_cards to mark cards as answered
        """
        
        llm_with_tools = self.llm.bind_tools([answer_card, answer_multiple_cards, check_anki_connection], temperature=self._get_temperature())
        
        response = await llm_with_tools.ainvoke([
            SystemMessage(content=system_prompt)]+ state["messages"])
        
        state["messages"].append(
            response
        )
        
        state["next"] = "topic_selection_prompt"  # After answering, go back to topic selection prompt
       
        return state

    async def _free_conversation_node(self, state: KotoriState) -> KotoriState:
        """Handle free-form conversation with tool access for adding Anki notes."""
        goals = state.get('learning_goals', 'general chat')
        language = self.config.get('language', 'english')
        
        # Set the calling node for proper routing after tools
        state["calling_node"] = "free_conversation"
        
        # Create a comprehensive system prompt for the LLM
        system_prompt = f"""You are Kotori, a friendly and helpful language learning assistant specialized in {language}.

CURRENT CONTEXT:
- Target language: {language}
- User's learning goals: {goals}

YOUR ROLE AND INSTRUCTIONS:
1. **Natural Conversation**: Engage in natural, flowing conversation that helps the user practice {language}
2. **Language Level Adaptation**:
   - Observe the user's {language} level from their messages
   - Adjust your language complexity accordingly (simpler for beginners, more natural for advanced)
3. **Learning Support**:
   - When the user struggles with a word, phrase, or concept, provide helpful explanations
   - Encourage the user and provide positive feedback on their progress
4. **Vocabulary Detection and Anki Integration**:
   - Pay attention to words or phrases the user doesn't know or uses incorrectly
   - If you notice the user struggling with specific vocabulary that would be useful for them to remember:
     * Use the add_anki_note tool to create a flashcard
     * Front: The word/phrase in {language} (keep it concise)
     * Back: Clear explanation with translation and example usage
   - Good candidates for Anki notes:
     * New vocabulary the user asks about
     * Words they misspell or misuse
     * Grammar points they struggle with
     * Useful phrases or expressions
5. **Conversation Flow**:
   - Keep the conversation engaging and relevant to their interests
   - Ask follow-up questions to encourage more practice
   - Introduce new vocabulary naturally when appropriate
   - If the conversation stagnates, suggest related topics or activities

TOOL USAGE GUIDELINES:
- Use add_anki_note strategically when you identify vocabulary the user should study
- Create clear, helpful flashcards with practical examples
- Don't overuse the tool - focus on genuinely useful vocabulary
- When you add a note, briefly mention it: "I've added that to your flashcards!"

RESPONSE STYLE:
- Be encouraging, patient, and conversational
- Respond primarily in {language} (adjust complexity based on user level)
- Provide English explanations when needed for clarity
- Keep responses natural and engaging, not overly formal or teacher-like
- Show enthusiasm for their learning progress

TOPIC MANAGEMENT:
- If the user seems to want to change topics, let the conversation flow naturally
- They can ask to "change topics" or "talk about something else" anytime

Continue the conversation naturally while being ready to help with vocabulary and learning opportunities."""

        # Use the full conversation history for context
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        
        # Bind the add_anki_note tool to the LLM with temperature
        llm_with_tools = self.llm.bind_tools([add_anki_note, check_anki_connection], temperature=self._get_temperature())
        
        # Generate response with tool access
        response = await llm_with_tools.ainvoke(messages)
        
        # Handle both string and message responses
        content = getattr(response, 'content', str(response))
        state["messages"].append(response)
        
        if tools_condition(state["messages"]) == "tools":
            # If tools were called, route to the tool node
            state["next"] = "tools"
            return state
        
        # Use interrupt to get user input
        user_input = interrupt(content)
        
        # Add both assistant message and user response to messages
        user_msg = HumanMessage(content=user_input)
        state["messages"].append(user_msg)
        state["counter"] = state.get("counter", 0) + 1
        
        # After assistant responds, route to evaluation to check user's next input
        # The evaluation node will determine whether to continue, assess, or change topics
        state["next"] = "free_conversation_eval"
        
        return state
    
    # Check if the user wants to continue free conversation
    # If no, go back to topic selection
    # If yes, evaluate the user's language and give feedback
    async def _free_conversation_eval_node(self, state: KotoriState) -> KotoriState:
        """Internal node - evaluate free conversation performance and determine next steps."""
        
        # Get the latest user message for evaluation
        last_user_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_user_message = msg
                break
        
        if not last_user_message:
            # No user message to evaluate, go back to topic selection
            state["next"] = "topic_selection_prompt"
            return state
        
        language = self.config.get('language', 'english')
        recent_messages = state["messages"][-6:] if len(state["messages"]) >= 6 else state["messages"]
        # First, check if the user wants to continue free conversation or change topics
        continue_conversation_prompt = f"""
        Analyze the user's latest message to determine their intent for the conversation flow.
        
        TARGET DECISION: Classify the user's intent into exactly ONE category.
        
        INPUT CONTEXT:
        - Recent message history: {recent_messages}
        - Current language focus: {language}
        
        CLASSIFICATION CRITERIA:
        1. "CONTINUE_FREE" if:
           - User is engaged in the current topic and wants to continue
           - They ask a follow-up question related to the current topic
           - They respond naturally without indicating desire for change or feedback
           - They request vocabulary help without asking for assessment
        
        2. "CHANGE_TOPIC" if:
           - User explicitly mentions wanting a different topic
           - They express boredom or disinterest in current conversation
           - They ask to switch to structured learning or flashcard practice
           - They indicate they're done with the current activity
           - They use phrases like "let's talk about X instead" or "can we try something else"
        
        3. "REQUEST_ASSESSMENT" if:
           - User explicitly asks for feedback on their language use
           - They ask how they're doing with grammar, vocabulary, or pronunciation
           - They ask if a sentence they wrote is correct
           - They request evaluation of their progress or skills
           - They produce a complex sentence that suggests they want feedback
        
        RESPONSE FORMAT:
        Return ONLY ONE of these exact strings without explanation:
        - "CONTINUE_FREE"
        - "CHANGE_TOPIC" 
        - "REQUEST_ASSESSMENT"
        
        EXAMPLES:
        "I enjoyed that story. Can you tell me another one?" → CONTINUE_FREE
        "I don't want to talk about this anymore. What else can we discuss?" → CHANGE_TOPIC
        "Did I use the past tense correctly in my last sentence?" → REQUEST_ASSESSMENT
        "Can we practice with flashcards now?" → CHANGE_TOPIC
        "How's my pronunciation?" → REQUEST_ASSESSMENT
        "What does this word mean?" → CONTINUE_FREE
        """
        
        conversation_decision_response = await self._get_configured_llm().ainvoke([
            SystemMessage(content=continue_conversation_prompt)
        ])
        
        conversation_decision = str(conversation_decision_response.content).strip()
        
        if "CHANGE_TOPIC" in conversation_decision:
            # User wants to change topics or switch to structured learning
            state["next"] = "topic_selection_prompt"
        elif "CONTINUE_FREE" in conversation_decision:
            # User is asking for something else
            state["next"] = "free_conversation"
        elif "REQUEST_ASSESSMENT" in conversation_decision:
            # User wants assessment on their language use
            await self._perform_free_conversation_assessment(state, last_user_message)
            state["next"] = "free_conversation"
        # else:
        #     # Continue free conversation - but periodically assess progress
        #     conversation_length = state.get("counter", 0)
            
        #     # Perform assessment every 5-7 user messages to track progress
        #     if conversation_length % 6 == 0:  # Every 6th user message
        #         await self._perform_free_conversation_assessment(state, last_user_message)
        #         state["next"] = "free_conversation"
        #     else:
        #         # Continue free conversation without assessment
        #         state["next"] = "free_conversation"
        
        return state
    
    async def _perform_free_conversation_assessment(self, state: KotoriState, user_message: HumanMessage) -> None:
        """Perform assessment of user's free conversation performance."""
        language = self.config.get('language', 'english')
        learning_goals = state.get('learning_goals', 'general conversation practice')
        
        # Get recent conversation context (last 6 messages)
        recent_messages = state["messages"][-6:] if len(state["messages"]) >= 6 else state["messages"]
        
        assessment_prompt = f"""
        You are assessing a language learner's conversation in {language}.
        
        Learning Goals: {learning_goals}
        
        Evaluate the user's messages on these simplified criteria:
        
        1. LANGUAGE USE: How well they use vocabulary and grammar
        2. COMMUNICATION: How effectively they express ideas and maintain conversation
        3. PROGRESS: Any improvement shown during the conversation
        
        Provide a brief assessment:
        LANGUAGE USE: [score 1-5] - [brief comment on vocabulary and grammar]
        COMMUNICATION: [score 1-5] - [comment on expression and conversation flow]
        PROGRESS: [score 1-5] - [note any improvement]
        OVERALL: [score 1-5] - [summary in 1-2 sentences]
        NEXT STEPS: [1-2 specific, actionable suggestions]
        """
        
        assessment_response = await self._get_configured_llm().ainvoke([
            SystemMessage(content=assessment_prompt)
        ] + recent_messages)
        
        # Print the assessment response for debugging
        print(f"Free Conversation Assessment Response: {assessment_response.content}")
        
        # Store the assessment in learning opportunities for later use
        current_assessment = f"Free Conversation Assessment - {user_message.content[:30]}...: {assessment_response.content}"
        assessment_history = state.get('assessment_history', [])
        assessment_history.append(current_assessment)
        state['assessment_history'] = assessment_history
        
    
    async def run_conversation(self, initial_state: Optional[KotoriState] = None, thread_id: str = "1"):
        """
        Main method to run the conversation using interrupts for user input.
        
        This method uses the checkpointer to maintain state and interrupts for user interaction.
        """
                
        if initial_state is None:
            initial_state = {
                "messages": [],
                "learning_goals": "",
                "next": "",
                "active_cards": "",
                "assessment_history": [],
                "calling_node": "",
                "counter": 0,
                "round_start_msg_idx": 0
            }
        
        # Configuration for the thread
        graphconfig = RunnableConfig(
            configurable={"thread_id": thread_id},
            recursion_limit=100
        )
        current_state = cast(KotoriState, initial_state)
        
        # Use streaming to process nodes one at a time
        try:
            needBreak = False
            resume = False
            
            while not needBreak:
                if not resume:
                    async for chunk in self.app.astream(cast(KotoriState, current_state), config=graphconfig):
                        # Get the current node and state from the chunk
                        current_node = list(chunk.keys())[0]
                        if current_node == "__interrupt__":
                            _print_interrupt(chunk)
                            resume = True
                            break
                        else:
                            current_state = cast(KotoriState, chunk[current_node])
                            next = self._route_next(current_state)
                            if next == END:
                                print("Learning session completed!")
                                return
                            print(f"Processed node: {current_node}")
                            print(f"Next state: {current_state.get('next', 'None')}")
                        # Check if we need user input
                else:
                    # ask user input
                    user_input = input("You: ")
                    if user_input.lower() in ["exit", "quit"]:
                        print("Exiting conversation.")
                        needBreak = True
                        break
                    
                    async for chunk in self.app.astream(Command(resume=user_input), config=graphconfig):
                        current_node = list(chunk.keys())[0]
                        if current_node == "__interrupt__":
                            _print_interrupt(chunk)
                            resume = True
                            break
                        else:
                            current_state = cast(KotoriState, chunk[current_node])
                            next = self._route_next(current_state)
                            if next == END:
                                print("Learning session completed!")
                                return
                            print(f"Processed node: {current_node}")
                            print(f"Next state: {current_state.get('next', 'None')}")
            
        except Exception as e:
            print(f"Error during graph execution: {e}")
            raise

def _print_interrupt(chunk: dict):
    """Print the interrupt message for debugging."""
    # {'__interrupt__': (Interrupt(value="Hello! I'm Kotori, your english learning assistant. What is your level and what would you like to learn today?", resumable=True, ns=['greeting:2da94e2a-2e8a-5872-0d84-2b9b5c98f7eb']),)}
    # print message:
    interrupt_tuple = chunk.get("__interrupt__")
    if interrupt_tuple:
        # get value from the interrupt tuple
        interrupt_value = interrupt_tuple[0].value
        print(f"Assistant: {interrupt_value}")
    else:
        print("No interrupt found in chunk.")