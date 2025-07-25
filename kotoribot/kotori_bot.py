from typing import Annotated, Dict, Any, List, Optional, cast

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent, ToolNode, tools_condition
from langgraph.types import Command, interrupt
from langchain_core.language_models import BaseLLM
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage, ToolCall
from langchain_core.language_models import BaseChatModel  # Change this import
from langchain_core.runnables import RunnableConfig
import re


from anki.anki import (
    add_anki_note,
    _check_anki_connection_internal,
    check_anki_connection,
    create_anki_deck,
    get_note_by_id,
    search_notes_by_content,
    find_cards_to_talk_about,
    answer_card,
    answer_multiple_cards,
    relearn_cards
)

class KotoriState(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]
    
    round_start_msg_idx: int  # Index of the message where the current round of conversation started
    
    learning_goals: str
    
    next: str # The next state to transition to
    
    card_answer_next: str # The next state after answering a card, if applicable, this is a temp workaround
    
    need_card_answer: bool  # Whether we need to answer a card in the current round
    
    active_cards: str
    
    assessment_history: List[str]
    
    calling_node: str  # Track which node called the tools
    
    counter: int
    
class KotoriConfig(TypedDict):
    language: str # possible values: "english" and "japanese"
    deck_name: Optional[str] # Name of the Anki deck to read, Kotori will always add cards to 'Kotori' deck
    temperature: Optional[float]  # Temperature for LLM responses, default is 0.1

def get_init_kotori_state() -> KotoriState:
    """Get the initial state for Kotori bot."""
    return {
        "messages": [],
        "round_start_msg_idx": 0,
        "learning_goals": "",
        "next": "",
        "card_answer_next": "",
        "active_cards": "",
        "assessment_history": [],
        "calling_node": "",
        "counter": 0,
        "need_card_answer": False
    }
    
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
        self.graph.add_node("mode_selection_prompt", self._mode_selection_prompt_node)
        self.graph.add_node("conversation", self._conversation_node)
        self.graph.add_node("free_conversation", self._free_conversation_node)
        
        # Internal processing nodes (no user input needed)
        self.graph.add_node("retrieve_cards", self._retrieve_cards_node)
        self.graph.add_node("assessment", self._assessment_node)
        self.graph.add_node("mode_selection", self._mode_selection_node)
        self.graph.add_node("free_conversation_eval", self._free_conversation_eval_node)
        # self.graph.add_node("card_answer", self._card_answer_node)
        
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
            ["mode_selection_prompt", "greeting", END]
        )
        
        self.graph.add_conditional_edges(
            "mode_selection_prompt",
            self._route_next,
            ["mode_selection"]
        )
        
        self.graph.add_conditional_edges(
            "mode_selection",
            self._route_next,
            ["retrieve_cards", "free_conversation"]
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
            ["assessment", "conversation", "mode_selection_prompt", "tools"]
        )
        
        self.graph.add_conditional_edges(
            "free_conversation",
            self._route_next,
            ["free_conversation_eval", "tools"]
        )
        
        # Assessment node can also use tools
        self.graph.add_conditional_edges(
            "assessment",
            self._route_next,
            ["conversation", "free_conversation", "retrieve_cards"]
        )
        
        # Card answer node can either use tools or go to next state
        # this could be removed
        # self.graph.add_conditional_edges(
        #     "card_answer",
        #     self._route_next,
        #     ["tools", "retrieve_cards", "free_conversation"]
        # )
        
        # After tools are executed, we need to route back to the calling node
        # We'll use a custom routing function to determine where to return
        self.graph.add_conditional_edges(
            "tools",
            self._route_after_tools,
            ["conversation", "mode_selection", "free_conversation"]
        )
        
        # Internal nodes route automatically
        self.graph.add_conditional_edges(
            "free_conversation_eval",
            self._route_next,
            ["mode_selection_prompt", "free_conversation", "retrieve_cards"]
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
        calling_node = state.get("calling_node", "mode_selection_prompt")
        
        # Validate that the calling node is a valid destination
        valid_destinations = ["card_answer", "conversation", "assessment", "mode_selection", "free_conversation"]
        
        if calling_node in valid_destinations:
            return calling_node
        else:
            # Fallback to mode_selection if invalid calling node
            return "mode_selection_prompt"
    
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
                greeting_prompt = f"""Hey! I'm Kotori 🐦 What's your {language} level? (beginner/intermediate/advanced). And what would you like to focus on today?"""
            elif language == "japanese":
                greeting_prompt = f"""こんにちは！コトリ 🐦 です。あなたの日本語レベルを教えてください（初級/中級/上級）。今日は何を勉強したいですか？"""
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
            state["next"] = "mode_selection_prompt"  # Move to topic selection
        else:
            # This shouldn't happen in normal flow, but handle gracefully
            state["next"] = "mode_selection_prompt"
        
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
    
    async def _mode_selection_prompt_node(self, state: KotoriState) -> KotoriState:
        """Generate assistant message for topic selection and get user input."""
        language = self.config.get('language', 'english')
        learning_goals = state.get("learning_goals", "general")
        
        # Create mode selection prompt based on language
        if language == "english":
            mode_prompt = """Great! Now, which mode would you like to try today?

📚 **Study mode**: I'll help you practice with your flashcards - we'll work on specific vocabulary and I'll give you feedback on your progress.

💬 **Chat mode**: We can just have a friendly conversation! I won't correct you unless you specifically ask for help.

Which sounds good to you - study mode or chat mode?"""
        elif language == "japanese":
            mode_prompt = """素晴らしい！今日はどのモードを試したいですか？

📚 **学習モード**：フラッシュカードで練習しましょう - 特定の語彙を練習して、進歩についてフィードバックします。

💬 **チャットモード**：友達のように会話しましょう！特別に助けを求めない限り、訂正しません。

どちらがいいですか - 学習モードかチャットモードか？"""
        else:
            mode_prompt = "Please select study mode or chat mode."
        
        # Use interrupt to get user input directly with the mode selection prompt
        user_input = interrupt(mode_prompt)
        
        # Add both assistant message and user response to messages
        state["messages"].append(AIMessage(content=mode_prompt))
        user_msg = HumanMessage(content=user_input)
        state["messages"].append(user_msg)
        
        state["next"] = "mode_selection"
        
        return state
        
    async def _mode_selection_node(self, state: KotoriState) -> KotoriState:
        """Internal node - select appropriate learning mode/ chat mode based on goals."""
        # This is an internal processing node - no assistant message

        # System prompt to determine if user wants study mode or chat mode
        system_prompt = f"""
You are a task manager. Given a user's recent message history, analyze and determine which mode they want to use.
Select the appropriate route based on the user's mode choice. Respond only with the chosen route's number.

Routes:
1. FREE_CONVERSATION: The user wants chat mode, free conversation, or casual talk.
2. GUIDED_CONVERSATION: The user wants study mode, flashcard practice, or structured learning.

Mode Selection Examples:
- "chat mode" -> 1
- "I want to chat" -> 1  
- "free conversation" -> 1
- "let's just talk" -> 1
- "chat mode please" -> 1
- "study mode" -> 2
- "flashcards" -> 2
- "I want to study" -> 2
- "practice with cards" -> 2
- "study mode please" -> 2

Topic Examples (if no clear mode is mentioned):
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
    
        topic_decision = str(topic_response.content).strip()
        
        state = self._reset_learning_states(state)
        if "1" in topic_decision:
            # User wants chat mode/free conversation
            state['next'] = 'free_conversation'
        else:
            # User wants study mode, go to retrieve cards
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
        state['card_answer_next'] = ''
        state['need_card_answer'] = False
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
        try:
            llm_with_tools = self.llm.bind_tools([add_anki_note, check_anki_connection], temperature=self._get_temperature())
        except:
            llm_with_tools = self.llm.bind_tools([add_anki_note, check_anki_connection])
        
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
            # state['need_card_answer'] = True  # Indicate we need to answer the card
            await self._do_card_answer(state, current_assessment, active_cards)

        return state

    async def _assessment_node(self, state: KotoriState) -> KotoriState:
        """Assess user's understanding on the active card."""    
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
    
        topic_decision = str(topic_response.content).strip()
        
        if "1" in topic_decision or "2" in topic_decision:
            if current_conversation_count > 0:
                state = await self._do_card_assessment(state, current_conversation_count)
        
        if "1" in topic_decision:
            state['next'] = 'free_conversation' 
            state = self._reset_learning_states(state)  # Reset learning states for next round
            state['card_answer_next'] = 'free_conversation'
        elif "2" in topic_decision:
            # User has demonstrated understanding or wants to change vocabulary
            state = self._reset_learning_states(state)  # Reset learning states for next round
            state['card_answer_next'] = 'retrieve_cards'
            state['next'] = 'retrieve_cards'  # Go to card answering node
        else: # Copilot might not know what to do, or it chooses 3, let's continue conversation
            state['next'] = 'conversation'
            
        return state
    
    async def _do_card_answer(self, state, assessment: str, card: str):
        """Perform the card answering logic based on assessment and card data."""
        # This function would typically interact with Anki to mark the card as answered
        # For now, we just simulate this action
        print(f"Answering card: {card} based on assessment: {assessment}")
        
        if card != "" and assessment != "":
            card_id = ""
            card_id_match = re.search(r'ID: (\d+)', card)
            
            if card_id_match:
                card_id = card_id_match.group(1)
            
            overall_mastery_match = re.search(r'OVERALL_MASTERY: (\d)', assessment)
            overall_mastery = 0
            if overall_mastery_match:
                try:
                    overall_mastery = int(overall_mastery_match.group(1))
                except ValueError:
                    overall_mastery = 0
                
                if overall_mastery >= 4:
                    overall_mastery = 4  # Use ease 4 for high mastery
            
            if card_id != "" and overall_mastery > 0:
                
                relearn_result = await relearn_cards.ainvoke({"card_ids": [card_id]})
                
                # Call the Anki tool to answer the card
                result = await answer_card.ainvoke({"card_id": card_id, "ease": overall_mastery})

                result = "Card call for ID: " + card_id + " with ease: " + str(overall_mastery) + ": " + str(relearn_result) + ", " + str(result)

                state["messages"].append(
                    ToolMessage(
                        name = "answer_card",
                        tool_call_id = "answer_card_" + card_id,
                        content=result
                    )
                )

    # async def _card_answer_node(self, state: KotoriState) -> KotoriState:
    #     """Handle answering a specific card using tools."""
        
    #     # First time in this node - decide what to do based on assessment
    #     assessment_history = state.get("assessment_history", [])
    #     active_cards = state.get("active_cards", "")
    #     need_card_answer = state.get("need_card_answer", False)

    #     # Do assessment to see if we need to answer the card
    #     if active_cards != "" and len(assessment_history) > 0 and need_card_answer:

    #         # Set the calling node for proper routing after tools
    #         state["calling_node"] = "card_answer"
            
    #         last_assessment = assessment_history[-1]
            
    #         # Create a prompt for the LLM to decide which tools to use
    #         system_prompt = f"""
    #         You are helping a language learner practice with Anki cards. 
            
    #         Current active cards: {active_cards}
    #         Last assessment: {last_assessment}

    #         Based on the last assessment and the cards they're working with, you should:
    #         Use answer_card to mark cards as answered based on the OVERALL_MASTERY, if the user got 4 or 5, use ease 4; otherwise, use ease the same as OVERALL_MASTERY.
    #         """
            
    #         user_prompt = "Please answer the active card based on the last assessment."
            
    #         try:
    #             llm_with_tools = self.llm.bind_tools([answer_card, check_anki_connection], temperature=self._get_temperature())
    #         except Exception as e:
    #             llm_with_tools = self.llm.bind_tools([answer_card, check_anki_connection])
            
    #         response = await llm_with_tools.ainvoke([
    #             SystemMessage(content=system_prompt),
    #             HumanMessage(content=user_prompt)
    #         ])

    #         state["messages"].append(
    #             response
    #         )
        
    #     next = state.get("card_answer_next", "retrieve_cards")
    #     if next == "":
    #         next = "retrieve_cards"  # Default to retrieving cards if not set
        
    #     state["next"] = next
    #     state = self._reset_learning_states(state)  # Reset learning states for next round
       
    #     return state

    async def _free_conversation_node(self, state: KotoriState) -> KotoriState:
        """Handle free-form conversation with tool access for adding Anki notes."""
        goals = state.get('learning_goals', 'general chat')
        language = self.config.get('language', 'english')
        
        # Set the calling node for proper routing after tools
        state["calling_node"] = "free_conversation"
        
        # Create a comprehensive system prompt for the LLM
        system_prompt = f"""You are Kotori, a friendly conversation partner who happens to speak {language}. Act like a casual friend having a relaxed chat.
CURRENT CONTEXT:
- Target language: {language}
- User's interests: {goals}
YOUR ROLE - BE A FRIEND, NOT A TEACHER:
1. **Casual Friend Mode**: 
   - Chat naturally like you're texting a friend
   - Focus on the conversation topic, not language learning
   - Be genuinely interested in what they're saying
   - React naturally to their thoughts and stories
2. **NO Unsolicited Corrections**:
   - NEVER correct grammar, pronunciation, or word choice unless explicitly asked
   - Ignore spelling mistakes and grammatical errors completely
   - Don't provide learning tips or feedback unless they ask for help
   - If you understand what they mean, just respond to the content
3. **Concise & Natural**:
   - Keep responses short and conversational (1-3 sentences typically)
   - Use natural {language} appropriate for casual conversation
   - Avoid teacher-like explanations or overly detailed responses
   - Match their energy and conversation style
4. **Help ONLY When Asked**:
   - Only provide language help when they explicitly ask: "What does X mean?", "How do I say Y?", "Is this correct?"
   - When they ask for help, give clear, concise explanations
   - Use add_anki_note tool only when they specifically ask you to add something to their flashcards
   - After helping, smoothly return to normal friend conversation
5. **Friend Conversation Priorities**:
   - Ask follow-up questions about their life, interests, stories
   - Share reactions and opinions naturally
   - Keep conversations flowing with genuine curiosity
   - Focus on connection and engagement over language practice

RESPONSE STYLE:
- Talk like a friend, not a language teacher
- Keep it brief and natural
- Respond primarily in {language} at an appropriate level for casual chat
- Only switch to "teacher mode" when explicitly requested
- Show genuine interest in them as a person, not as a language learner

TOOL USAGE:
- Use add_anki_note ONLY when they explicitly ask to add something to flashcards
- Don't proactively suggest vocabulary additions
- When adding notes, keep it brief: "Added!" or "Got it in your flashcards!"

Remember: You're their friend first, language helper second. Let them drive when they want language assistance."""

        # Use the full conversation history for context
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        
        # Bind the add_anki_note tool to the LLM with temperature
        try:
            llm_with_tools = self.llm.bind_tools([add_anki_note, check_anki_connection], temperature=self._get_temperature())
        except Exception as _:
            llm_with_tools = self.llm.bind_tools([add_anki_note, check_anki_connection])
        
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
            state["next"] = "mode_selection_prompt"
            return state
        
        language = self.config.get('language', 'english')
        learning_goals = state.get('learning_goals', 'general conversation')
        
        # Get recent messages for context
        user_history = self._get_recent_messages(state, count=10)
        
        route_next_system_prompt = f"""
You are a task manager for {language} free conversation evaluation. Given a user's recent message history during free conversation, analyze and determine the next route.
Select the appropriate route based on the user's intent and learning preferences. Respond only with the chosen route's number.

CURRENT CONTEXT:
- Target language: {language}
- User's level and learning goal: {learning_goals}

Routes:
1. CONVERSATION: The user wants to learn vocabulary instead of just chatting OR explicitly requests structured learning OR wants to practice with flashcards.
2. FREE_CONVERSATION: The user wants to keep chatting freely OR asks questions OR continues the current topic naturally OR requests help with vocabulary during conversation.

KEY INSIGHTS: Adding the active card to Anki means they are still engaged with the free conversation → Route 2

Examples:
CONVERSATION (Route 1):
- "Can we practice some vocabulary?" → 1
- "I want to study flashcards now" → 1
- "Let's do some structured learning" → 1
- "Can we switch to study mode?" → 1

FREE_CONVERSATION (Route 2):
- "What does 'beautiful' mean?" → 2
- "I enjoyed that story. Can you tell me another one?" → 2
- "That's interesting! Tell me more about it" → 2
- "How do you say 'dog' in {language}?" → 2
- User continues conversation naturally → 2
- "I like talking about this topic" → 2
- User asks follow-up questions about the current topic → 2
- "Put the word 'tree' into anki." → 2
"""

        user_input = str(
            "recent messages: {{{" + " ".join([f"[{msg.__class__.__name__}] {str(msg.content)}" for msg in user_history]) + "}}} Remember you must only output a number which corresponds to a route. "
            "given above based on your understanding of the recent messages and the user's intent."
        )
        
        topic_response = await self._get_configured_llm().ainvoke([
            SystemMessage(content=route_next_system_prompt),
            HumanMessage(content=user_input)
        ])
    
        topic_decision = str(topic_response.content).strip()
        
        if "1" in topic_decision:
            # User wants to learn vocabulary instead of chat
            state = self._reset_learning_states(state)  # Reset learning states for new topic
            state["next"] = "retrieve_cards"  # Go to card retrieval node
        else:
            # User wants to keep chatting freely
            state = await self._perform_free_conversation_assessment(state)
            state["next"] = "free_conversation"
        
        return state
    
    async def _perform_free_conversation_assessment(self, state: KotoriState) -> KotoriState:
        """Perform assessment of user's free conversation performance."""
        language = self.config.get('language', 'english')
        learning_goals = state.get('learning_goals', 'general conversation practice')

        # Get recent conversation context (last 10 messages)
        user_history = self._get_recent_messages(state, count=10)
        user_last_message = self._get_recent_messages(state, count=1)
        
        if len(user_last_message) > 0:
            user_message = user_last_message[0]
        
            assessment_prompt = f"""
You are a friendly native {language} speaker helping someone sound more natural. Focus on making their {language} flow like a native speaker's.

User's level: {learning_goals}
            
Analyze their latest message for naturalness and provide brief, helpful feedback. Choose only ONE aspect that would be most helpful:

GRAMMAR CORRECTION: [If there are grammar errors, provide the corrected version. Ignore punctuation and spelling mistakes unless they affect meaning. Focus on common errors that would be noticeable to a native speaker.]

NATURAL EXPRESSION: [If their message sounds unnatural or awkward, suggest how a native speaker would express the same idea. Focus on authentic word choice, idiomatic phrasing, and conversational flow rather than technical grammar rules. For advanced users, highlight subtle nuances that would make their speech sound more authentic.]

CULTURAL/CONTEXTUAL NOTES: [If relevant, mention how natives actually use these words/phrases in real conversation]

Keep feedback encouraging and practical. Focus on the MOST impactful improvement rather than covering everything.
            """
            
            user_input = str(
            "recent messages: {{{" + " ".join([f"[{msg.__class__.__name__}] {str(msg.content)}" for msg in user_history]) + "}}}, last message to assess: {{{" + str(user_message.content) + """}}} Please assess the naturalness of the user's last message according to the guidelines. If the message already sounds natural and native-like, or if they're asking for help/clarification, respond with "NO_ASSESSMENT" """
            )
            
            assessment_response = await self._get_configured_llm().ainvoke([
                SystemMessage(content=assessment_prompt),
                HumanMessage(content=user_input)
            ])
            
            if "no_assessment" in str(assessment_response.content).lower():
                print("No assessment needed for the user's last message.")
                return
            
            # Print the assessment response for debugging
            print(f"Free Conversation Assessment Response: {assessment_response.content}")
            
            # Store the assessment in learning opportunities for later use
            current_assessment = f"Free Conversation Assessment - {user_message.content[:30]}...: {assessment_response.content}"
            assessment_history = state.get('assessment_history', [])
            assessment_history.append(current_assessment)
            state['assessment_history'] = assessment_history
        
        return state
    
    async def run_conversation(self, initial_state: Optional[KotoriState] = None, thread_id: str = "1"):
        """
        Main method to run the conversation using interrupts for user input.
        
        This method uses the checkpointer to maintain state and interrupts for user interaction.
        """
                
        if initial_state is None:
            initial_state = get_init_kotori_state()
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