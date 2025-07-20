from typing import Annotated, Dict, Any, List, Optional, cast

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent, ToolNode, tools_condition
from langgraph.types import Command, interrupt
from langchain_core.language_models import BaseLLM
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
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
    
    learning_goals: str
    
    next: str # The next state to transition to
    
    active_cards: str
    
    assessment_history: str
    
    learning_opportunities: str
    
    calling_node: str  # Track which node called the tools

    
class KotoriConfig(TypedDict):
    language: str # possible values: "english" and "japanese"
    deck_name: Optional[str] # Name of the Anki deck to use
    
    
class KotoriBot:
    """Language learning bot that manages conversation flow and learning state."""
    def __init__(self, llm: BaseChatModel, config: KotoriConfig):
        # Initialize the state graph with the defined state schema
        self.graph = StateGraph(state_schema=KotoriState)
        
        self.llm = llm
        self.config = config
        
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
            ["assessment", "topic_selection_prompt", END]
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
    
    
    async def _topic_selection_prompt_node(self, state: KotoriState) -> KotoriState:
        """Generate assistant message for topic selection and get user input."""
        language = self.config.get('language', 'english')
        learning_goals = state.get("learning_goals", "general")
        system_prompt = '''
            You are Kotori, a friendly and helpful language learning assistant specialized in teaching {language}.
            
            Based on the conversation history and the user's learning goals {learning_goals}, ask the user if they have a specific topic they would like to discuss.
            
            Keep your message encouraging, concise, and end with a clear question about if they want to discuss a specific topic.
            
            Respond naturally in {language} if the user's level seems intermediate or above, otherwise use simpler {language}.
        '''
        system_prompt = system_prompt.format(language=language, learning_goals=learning_goals)
        
        user_messages_history = state["messages"]
        
        topic_msg = await self.llm.ainvoke([
            SystemMessage(content=system_prompt)
        ]+ user_messages_history)
        
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
        last_human_message = state['messages'][-1]
        language = self.config.get('language', 'english')
        
        # System prompt to determine if user has a specific topic they want to discuss
        system_prompt = """
        Analyze the user's message to determine if they have a specific topic they want to discuss.
        
        Respond with exactly one of these:
        - "HAS_TOPIC" if the user mentions a specific topic, subject, or theme they want to talk about
        - "NO_TOPIC" if the user doesn't have a specific topic, says no, or asks for suggestions
        
        Examples:
        - "I want to talk about cooking" -> HAS_TOPIC
        - "Let's discuss Japanese culture" -> HAS_TOPIC
        - "I want to do free talk" -> HAS_TOPIC
        - "No, I don't have anything specific" -> NO_TOPIC
        - "What should we talk about?" -> NO_TOPIC
        - "I'm not sure" -> NO_TOPIC
        """
        
        topic_response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_human_message.content)
        ])
    
        topic_decision = str(topic_response).strip()
        
        if "HAS_TOPIC" in topic_decision:
            # User has a topic, transition to free conversation
            state = self._reset_learning_states(state)
            state['next'] = 'free_conversation'
        else:
            # User doesn't have a topic, try to find Anki cards to discuss
            try:
                # Try to find cards from Anki to discuss
                deck_name = self.config.get('deck_name', 'Kotori')  # Default deck name
                cards_result = find_cards_to_talk_about.invoke({"deck_name": deck_name, "limit": 3})
                
                # Parse the result to check if cards were found
                if "Error" in cards_result or "No cards found" in cards_result:
                    # No cards found, transition to free conversation
                    state = self._reset_learning_states(state)
                    state['next'] = 'free_conversation'
                        
                else:
                    # Cards found, transition to structured conversation
                    state = self._reset_learning_states(state)
                    state['next'] = 'conversation'
                    # Note: In a real implementation, you'd parse the cards_result 
                    # and store the card data in state['active_cards']
                    state['active_cards'] = cards_result
            
            except Exception as e:
                # Error accessing Anki, fallback to free conversation
                state = self._reset_learning_states(state)
                state['next'] = 'free_conversation'
    
        return state
    
    def _reset_learning_states(self, state: KotoriState) -> KotoriState:
        """Reset learning-related states to prepare for a new topic."""
        state['active_cards'] = ''
        state['learning_goals'] = ''
        state['assessment_history'] = ''
        state['learning_opportunities'] = ''
        return state
    
    async def _conversation_node(self, state: KotoriState) -> KotoriState:
        """Handle structured conversation with learning cards."""
        # Generate assistant message for conversation
        active_cards = state.get("active_cards", "general topics")
        goals = state.get('learning_goals', 'general practice')
        language = self.config.get('language', 'english')
        deck = self.config.get('deck_name', 'Kotori')  # Default deck name
        learning_goal = state.get('learning_goals', 'general conversation')
        
        # Create a simple prompt for the LLM
        system_message = SystemMessage(content=f"""
        You are Kotori, a helpful language learning assistant specialized in {language}. The user has the following learning goals: {learning_goal}.

        INSTRUCTIONS:
        1. Create a natural conversation that incorporates at least one of vocabulary from these cards: {active_cards}
        2. Focus on the user's learning goals: {goals}
        3. Weave the vocabulary naturally into the conversation - don't explicitly mention you're using specific cards
        4. Match your language complexity to the user's apparent level:
            - Use natural {language} for intermediate or advanced learners
            - Use simpler {language} for beginners
        5. If the user struggles with a word NOT in the active cards, use the add_anki_note tool to add it to their '{deck}' deck

        Your purpose is to create an engaging, helpful learning experience that feels natural while reinforcing vocabulary. Please respond clearly and concisely in {language}.
        """)
        
        prompt = [system_message] + state["messages"]
        
        llm_with_tools = self.llm.bind_tools([add_anki_note, check_anki_connection])
        
        response = await llm_with_tools.ainvoke([
            system_message]+ state["messages"])
        
        # Handle both string and message responses
        content = getattr(response, 'content', str(response))
        
        # Use interrupt to get user input
        user_input = interrupt(content)
        
        # Add both assistant message and user response to messages
        ai_msg = AIMessage(content=content)
        state["messages"].append(ai_msg)
        user_msg = HumanMessage(content=user_input)
        state["messages"].append(user_msg)
        
        state["next"] = "assessment"  # Move to assessment
        
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
        
        # First, check if the user wants to continue the current topic
        continue_topic_prompt = f"""
        Analyze the user's message to determine if they want to continue discussing the current topic or if they want to change topics.
        
        Look for signals like:
        - Asking to change topics or talk about something else
        - Expressing that they're done with the current subject
        - Asking for a new topic or different conversation
        - Saying they want to move on
        
        Respond with exactly one of:
        - "CONTINUE" if they want to keep discussing the current topic
        - "CHANGE_TOPIC" if they want to change topics or are done with current discussion
        """
        
        topic_decision_response = await self.llm.ainvoke([
            SystemMessage(content=continue_topic_prompt)
        ] + state["messages"])
        
        topic_decision = str(topic_decision_response.content).strip()
        
        if "CHANGE_TOPIC" in topic_decision:
            # User wants to change topics
            assessment_history = state.get("assessment_history", "")
            
            if assessment_history:
                # There's assessment history, proceed to card answering
                state["next"] = "card_answer"
            else:
                # No assessment history, go back to topic selection
                state["next"] = "topic_selection_prompt"
        else:
            # User wants to continue - perform assessment on their message
            assessment_prompt = f"""
            You are assessing a language learner's understanding of specific vocabulary in {language}. Assess the latest user message based on the active cards.
            
            Current active vocabulary: {active_cards}
            
            Analyze the user's latest message to evaluate:
            1. Correct usage of target vocabulary from the active cards
            2. Demonstrated comprehension of the vocabulary meaning
            3. Appropriate contextual usage of the vocabulary
            
            Provide a brief assessment in this format:
            VOCABULARY_USAGE: [score 1-5] - [comment on how correctly they used the vocabulary]
            COMPREHENSION: [score 1-5] - [comment on their understanding of the vocabulary meaning]
            CONTEXT: [score 1-5] - [comment on appropriate contextual usage]
            OVERALL: [score 1-5] - [overall assessment of vocabulary mastery]
            NEXT_STEPS: [specific suggestion for vocabulary improvement briefly]
            """
            
            recent_messages = state["messages"][-6:] if len(state["messages"]) >= 6 else state["messages"]
            
            assessment_response = await self.llm.ainvoke([
                SystemMessage(content=assessment_prompt)
            ] + recent_messages)
            
            # Print the assessment response for debugging
            print(f"Assessment Response: {assessment_response.content}")
            
            # Append the assessment to assessment history
            current_assessment = f"Assessment of message '{last_user_message.content[:50]}...': {assessment_response.content}\n\n"
            state["assessment_history"] = state.get("assessment_history", "") + " " + current_assessment
            
            # Continue the conversation
            state["next"] = "conversation"
        
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
        
        llm_with_tools = self.llm.bind_tools([answer_card, answer_multiple_cards, check_anki_connection])
        
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
        deck_name = self.config.get('deck_name', 'Kotori')
        
        # Set the calling node for proper routing after tools
        state["calling_node"] = "free_conversation"
        
        # Create a comprehensive system prompt for the LLM
        system_prompt = f"""You are Kotori, a friendly and helpful language learning assistant specialized in {language}.

CURRENT CONTEXT:
- Target language: {language}
- User's learning goals: {goals}
- Available Anki deck: {deck_name}

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
     * Always use deck_name: "{deck_name}"
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
        
        # Bind the add_anki_note tool to the LLM
        llm_with_tools = self.llm.bind_tools([add_anki_note, check_anki_connection])
        
        # Generate response with tool access
        response = await llm_with_tools.ainvoke(messages)
        
        # Handle both string and message responses
        content = getattr(response, 'content', str(response))
        
        # Use interrupt to get user input
        user_input = interrupt(content)
        
        # Add both assistant message and user response to messages
        state["messages"].append(response)
        user_msg = HumanMessage(content=user_input)
        state["messages"].append(user_msg)
        
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
        
        # First, check if the user wants to continue free conversation or change topics
        continue_conversation_prompt = f"""
        Analyze the user's message to determine if they want to continue the current free conversation or if they want to change topics/end the conversation.
        
        Look for signals like:
        - Asking to change topics or talk about something else
        - Expressing that they're done with the current conversation
        - Asking for structured practice or specific activities
        - Saying they want to move on or try something different
        - Requesting to work on cards or specific vocabulary
        
        Respond with exactly one of:
        - "CONTINUE_FREE" if they want to keep having free conversation
        - "CHANGE_TOPIC" if they want to change topics or switch to structured learning
        - "REQUEST_ASSESSMENT" if they're asking for feedback on their language use
        """
        
        conversation_decision_response = await self.llm.ainvoke([
            SystemMessage(content=continue_conversation_prompt)
        ] + state["messages"])
        
        conversation_decision = str(conversation_decision_response.content).strip()
        
        if "CHANGE_TOPIC" in conversation_decision:
            # User wants to change topics or switch to structured learning
            state["next"] = "topic_selection_prompt"
        elif "REQUEST_ASSESSMENT" in conversation_decision:
            # User is asking for feedback, perform assessment
            await self._perform_free_conversation_assessment(state, last_user_message)
            state["next"] = "assessment"
        else:
            # Continue free conversation - but periodically assess progress
            conversation_length = len([msg for msg in state["messages"] if isinstance(msg, HumanMessage)])
            
            # Perform assessment every 5-7 user messages to track progress
            if conversation_length % 6 == 0:  # Every 6th user message
                await self._perform_free_conversation_assessment(state, last_user_message)
                state["next"] = "assessment"
            else:
                # Continue free conversation without assessment
                state["next"] = "free_conversation"
        
        return state
    
    async def _perform_free_conversation_assessment(self, state: KotoriState, user_message: HumanMessage) -> None:
        """Perform assessment of user's free conversation performance."""
        language = self.config.get('language', 'english')
        learning_goals = state.get('learning_goals', 'general conversation practice')
        
        # Get recent conversation context (last 6 messages)
        recent_messages = state["messages"][-6:] if len(state["messages"]) >= 6 else state["messages"]
        
        assessment_prompt = f"""
        You are assessing a language learner's free conversation performance in {language}.
        
        Learning Goals: {learning_goals}
        
        Evaluate the user's latest message and recent conversation performance on:
        
        1. FLUENCY: How naturally and smoothly they express ideas
        2. VOCABULARY: Range and appropriateness of vocabulary used
        3. GRAMMAR: Accuracy of grammatical structures
        4. ENGAGEMENT: How well they maintain and contribute to conversation
        5. PROGRESS: Improvement compared to earlier messages in the conversation
        
        Provide assessment in this format:
        FLUENCY: [score 1-5] - [brief comment on natural expression and flow]
        VOCABULARY: [score 1-5] - [comment on vocabulary range and usage]
        GRAMMAR: [score 1-5] - [comment on grammatical accuracy]
        ENGAGEMENT: [score 1-5] - [comment on conversation participation]
        PROGRESS: [score 1-5] - [comment on improvement during this conversation]
        OVERALL: [score 1-5] - [overall performance summary]
        STRENGTHS: [what they're doing well]
        AREAS_FOR_IMPROVEMENT: [specific suggestions for improvement]
        ENCOURAGEMENT: [positive, motivating feedback]
        """
        
        assessment_response = await self.llm.ainvoke([
            SystemMessage(content=assessment_prompt)
        ] + recent_messages)
        
        # Print the assessment response for debugging
        print(f"Free Conversation Assessment Response: {assessment_response.content}")
        
        # Store the assessment in learning opportunities for later use
        current_assessment = f"Free Conversation Assessment - {user_message.content[:30]}...: {assessment_response.content}\n\n"
        state["learning_opportunities"] = state.get("learning_opportunities", "") + current_assessment
        
        # Also add to assessment history for consistency with other assessment flows
        state["assessment_history"] = state.get("assessment_history", "") + current_assessment
    
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
                "assessment_history": "",
                "learning_opportunities": "",
                "calling_node": ""
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
                            next = current_state.get("next", END)
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
                            next = current_state.get("next", END)
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