import asyncio
import uuid
from typing import Optional, Dict, Any, AsyncIterator, Callable, cast
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

# Import the existing KotoriBot classes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from kotoribot.kotori_bot import KotoriBot, KotoriState, KotoriConfig as OriginalKotoriConfig, get_init_kotori_state
from ..models import Message, MessageType, StateInfo, ToolCall, AssessmentMetrics


class KotoriBotAdapter:
    """Adapter class that wraps the original KotoriBot for web interface."""
    
    def __init__(self, llm, config: Dict[str, Any]):
        # Convert our config format to the original format
        original_config: OriginalKotoriConfig = {
            "language": config.get("language", "english"),
            "deck_name": config.get("deck_name", "Kotori"),
            "temperature": config.get("temperature", 0.7),
        }
        
        self.kotori_bot = KotoriBot(llm, original_config)
        self.session_id = str(uuid.uuid4())
        self.state_callbacks: Dict[str, Callable] = {}
        self.tool_callbacks: Dict[str, Callable] = {}
        self.current_state: Optional[KotoriState] = None
        self.conversation_active = False
        self.sent_message_contents: set = set()  # Track sent message contents to prevent duplicates
        self.sent_message_hashes: set = set()  # Track content hashes for similarity detection
        self.last_interrupt_time: Optional[float] = None  # Track timing of last interrupt
        self.last_interrupt_content: Optional[str] = None  # Track last interrupt content
        self.interrupt_cooldown = 0.5  # Minimum seconds between interrupts
        self.interrupt_lock = asyncio.Lock()  # Lock to prevent concurrent interrupt processing
        
        # Override the interrupt method to handle web interface
        self._setup_interrupt_handler()
    
    def _setup_interrupt_handler(self):
        """Setup custom interrupt handling for web interface."""
        # Store original methods
        self.original_interrupt = None
        
        # We'll handle interrupts differently for web interface
        self.pending_response = None
        self.waiting_for_input = False
        self.input_queue = asyncio.Queue()
    
    async def start_conversation(self, initial_state: Optional[Dict[str, Any]] = None) -> str:
        """Start a new conversation session."""
        # For new conversations, we let the graph start from the beginning
        # The checkpointer will maintain state across sessions
        
        # Only set initial state for the very first run
        # After that, let the checkpointer handle state management
        if initial_state is None:
            self.current_state = get_init_kotori_state()
        else:
            self.current_state = cast(KotoriState, initial_state)
            
        self.conversation_active = True
        
        # Clear message tracking for new conversation
        self.sent_message_contents.clear()
        self.sent_message_hashes.clear()
        self.last_interrupt_time = None
        self.last_interrupt_content = None
        
        # Start the conversation in a background task with error handling
        task = asyncio.create_task(self._run_conversation_loop())
        
        # Add error handler for the background task
        def handle_task_exception(task):
            if task.exception():
                print(f"Conversation loop error for session {self.session_id}: {task.exception()}")
        
        task.add_done_callback(handle_task_exception)
        
        return self.session_id
    
    async def _run_conversation_loop(self):
        """Main conversation loop following the original kotori_bot.py pattern."""
        # Configuration for the thread - use the session_id as thread_id
        graphconfig = RunnableConfig(
            configurable={"thread_id": self.session_id},
            recursion_limit=100
        )
        
        try:
            # Follow the pattern from the original run_conversation method
            need_break = False
            resume = False
            processing_stream = False
            initial_run = True  # Track if this is the first run
            
            while self.conversation_active and not need_break:
                try:
                    if not resume and not processing_stream:
                        # Start new conversation flow - let the graph manage its own state
                        print(f"=== STARTING CONVERSATION STREAM ===")
                        print(f"Initial run: {initial_run}")
                        print(f"Resume: {resume}")
                        print(f"Processing stream: {processing_stream}")
                        print(f"Waiting for input: {self.waiting_for_input}")
                        
                        processing_stream = True
                        try:
                            # Only pass initial state on the very first run
                            # After that, let the checkpointer manage state
                            if initial_run:
                                stream_input = self.current_state
                                initial_run = False
                                print(f"Using initial state for first run")
                            else:
                                # For subsequent runs, don't pass state - let checkpointer handle it
                                stream_input = None
                                print(f"Using checkpointer state for subsequent run")
                            
                            async for chunk in self.kotori_bot.app.astream(stream_input, config=graphconfig):
                                current_node = list(chunk.keys())[0]
                                print(f"=== CHUNK: {current_node} ===")
                                
                                if current_node == "__interrupt__":
                                    print(f"Handling interrupt in node {current_node}")
                                    await self._handle_interrupt(chunk)
                                    resume = True
                                    print(f"Interrupt handled, resume set to {resume}")
                                    break
                                else:
                                    # Update our current state from the chunk
                                    print(f"Updating state from node {current_node}")
                                    self.current_state = cast(KotoriState, chunk[current_node])
                                    await self._handle_state_update(current_node, self.current_state)
                                    
                                    # Check if conversation ended using the bot's routing logic
                                    next_state = self.kotori_bot._route_next(self.current_state)
                                    print(f"Next state: {next_state}")
                                    if next_state == "END":
                                        print("Learning session completed!")
                                        self.conversation_active = False
                                        await self._notify_conversation_end()
                                        return
                        finally:
                            processing_stream = False
                            print(f"=== END CONVERSATION STREAM ===")
                    else:
                        # Resume with user input
                        try:
                            user_input = await asyncio.wait_for(self.input_queue.get(), timeout=300)  # 5 min timeout
                            print(f"User input received: {user_input}")
                            
                            if user_input.lower() in ["exit", "quit"]:
                                print("User requested exit")
                                need_break = True
                                break
                            
                            if not processing_stream:
                                processing_stream = True
                                try:
                                    # Resume with the user input using Command - this preserves state
                                    async for chunk in self.kotori_bot.app.astream(Command(resume=user_input), config=graphconfig):
                                        current_node = list(chunk.keys())[0]
                                        print(f"Processing node after resume: {current_node}")
                                        
                                        if current_node == "__interrupt__":
                                            await self._handle_interrupt(chunk)
                                            resume = True
                                            break
                                        else:
                                            # Update our current state from the chunk
                                            self.current_state = cast(KotoriState, chunk[current_node])
                                            await self._handle_state_update(current_node, self.current_state)
                                            
                                            # Check if conversation ended
                                            next_state = self.kotori_bot._route_next(self.current_state)
                                            print(f"Next state after resume: {next_state}")
                                            if next_state == "END":
                                                print("Learning session completed!")
                                                self.conversation_active = False
                                                await self._notify_conversation_end()
                                                return
                                    
                                    # Reset resume flag after processing
                                finally:
                                    processing_stream = False
                            else:
                                print("Stream processing already in progress, skipping duplicate resume")
                        except asyncio.TimeoutError:
                            print("Session timeout")
                            self.conversation_active = False
                            await self._notify_session_timeout()
                            return
                        except Exception as e:
                            print(f"Error in conversation resume: {e}")
                            await self._notify_error(f"Conversation resume error: {str(e)}")
                            processing_stream = False
                            continue
                            
                except Exception as e:
                    print(f"Error in conversation flow: {e}")
                    await self._notify_error(f"Conversation flow error: {str(e)}")
                    processing_stream = False
                    # Wait before retrying
                    await asyncio.sleep(1)
                    continue
                        
        except Exception as e:
            print(f"Error during graph execution: {e}")
            await self._notify_error(f"Conversation error: {str(e)}")
            self.conversation_active = False
    
    async def _handle_interrupt(self, chunk: Dict[str, Any]):
        """Handle interrupt events (AI asking for user input) with aggressive duplicate prevention."""
        # Use lock to prevent concurrent processing of interrupts
        async with self.interrupt_lock:
            interrupt_tuple = chunk.get("__interrupt__")
            if interrupt_tuple:
                interrupt_value = interrupt_tuple[0].value
                original_content = str(interrupt_value)
                
                print(f"=== INTERRUPT DEBUG ===")
                print(f"Raw interrupt content: {original_content}")
                print(f"Interrupt namespace: {interrupt_tuple[0].ns if hasattr(interrupt_tuple[0], 'ns') else 'N/A'}")
                print(f"Current waiting_for_input: {self.waiting_for_input}")
                
                # IMMEDIATE RETURN if already waiting for input - this prevents duplicate processing
                if self.waiting_for_input:
                    print(f"Already waiting for input, ignoring duplicate interrupt")
                    return
                
                # Set waiting_for_input BEFORE sending message to prevent race conditions
                self.waiting_for_input = True
                
                print(f"SENDING: {original_content[:50]}...")
                
                # Create AI message
                ai_message = Message(
                    id=str(uuid.uuid4()),
                    content=interrupt_value,
                    message_type=MessageType.AI,
                    timestamp=datetime.now(),
                    tool_calls=None  # Tool calls will be populated separately if needed
                )
                
                # Notify about AI response
                if "ai_response" in self.state_callbacks:
                    await self.state_callbacks["ai_response"](ai_message)
                
                print(f"=== END INTERRUPT DEBUG ===")
    
    async def _handle_state_update(self, node_name: str, state: KotoriState):
        """Handle state updates from the conversation."""
        self.current_state = state
        
        # Create state info
        state_info = StateInfo(
            current_node=node_name,
            next_node=state.get("next"),
            learning_goals=state.get("learning_goals", ""),
            active_cards=state.get("active_cards", ""),
            assessment_history=state.get("assessment_history", []),
            counter=state.get("counter", 0)
        )
        
        # Notify about state change
        if "state_change" in self.state_callbacks:
            await self.state_callbacks["state_change"](state_info)
        
        # Handle tool calls if present
        print(f"=== CHECKING FOR TOOL CALLS IN STATE ===")
        print(f"State keys: {list(state.keys()) if hasattr(state, 'keys') else 'No keys method'}")
        print(f"State type: {type(state)}")
        print(f"Messages key exists: {'messages' in state}")
        
        extracted_tool_calls = []
        
        if 'messages' in state and state['messages']:
            print(f"Number of messages: {len(state['messages'])}")
            last_message = state['messages'][-1]
            print(f"Last message type: {type(last_message)}")
            print(f"Last message content: {getattr(last_message, 'content', 'No content')[:100]}...")
            
            # Check if this is a ToolMessage (result of tool execution)
            from langchain_core.messages import ToolMessage
            if isinstance(last_message, ToolMessage):
                print(f"Found ToolMessage with result!")
                print(f"Tool name: {getattr(last_message, 'name', 'unknown')}")
                print(f"Tool call ID: {getattr(last_message, 'tool_call_id', 'unknown')}")
                print(f"Tool result content: {last_message.content[:200]}...")
                
                # Create a completed tool call
                tool_info = ToolCall(
                    tool_name=getattr(last_message, 'name', 'unknown_tool'),
                    parameters={},  # ToolMessage doesn't contain original parameters
                    status="success",
                    result=str(last_message.content) if last_message.content else None
                )
                print(f"Created completed tool info: {tool_info}")
                extracted_tool_calls.append(tool_info)
                
                if "tool_call" in self.tool_callbacks:
                    print(f"Calling tool_call callback for completed tool")
                    await self.tool_callbacks["tool_call"](tool_info)
                else:
                    print(f"No tool_call callback registered")
            
            # Also check for tool_calls attribute (pending tool calls) - but not on ToolMessage
            elif hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                print(f"Tool calls: {last_message.tool_calls}")
                print(f"Found {len(last_message.tool_calls)} pending tool calls")
                for i, tool_call in enumerate(last_message.tool_calls):
                    print(f"Tool call {i}: {tool_call}")
                    
                    # Handle different tool call formats
                    if hasattr(tool_call, 'name'):
                        tool_name = tool_call.name
                        parameters = getattr(tool_call, 'args', {})
                    elif isinstance(tool_call, dict):
                        tool_name = tool_call.get('name', 'unknown')
                        parameters = tool_call.get('args', {})
                    else:
                        tool_name = str(tool_call)
                        parameters = {}
                    
                    tool_info = ToolCall(
                        tool_name=tool_name,
                        parameters=parameters,
                        status="pending"
                    )
                    print(f"Created pending tool info: {tool_info}")
                    extracted_tool_calls.append(tool_info)
                    
                    if "tool_call" in self.tool_callbacks:
                        print(f"Calling tool_call callback for pending tool")
                        await self.tool_callbacks["tool_call"](tool_info)
                    else:
                        print(f"No tool_call callback registered")
            else:
                print(f"No tool_calls attribute or empty tool calls on last message")
        else:
            print(f"No messages in state or messages list is empty")
            print(f"State messages value: {state.get('messages', 'KEY_NOT_FOUND')}")
        
        # If we found tool calls, create a tool message to send to frontend
        if extracted_tool_calls:
            print(f"Creating tool message with {len(extracted_tool_calls)} tool calls")
            tool_message = Message(
                id=str(uuid.uuid4()),
                content=f"Tool calls processed: {', '.join([f'{tc.tool_name} ({tc.status})' for tc in extracted_tool_calls])}",
                message_type=MessageType.TOOL,
                timestamp=datetime.now(),
                tool_calls=extracted_tool_calls,
                metadata={
                    "tool_count": len(extracted_tool_calls),
                    "tool_names": [tc.tool_name for tc in extracted_tool_calls],
                    "completed_count": len([tc for tc in extracted_tool_calls if tc.status == "success"]),
                    "pending_count": len([tc for tc in extracted_tool_calls if tc.status == "pending"])
                }
            )
            
            # Notify about tool message
            if "tool_message" in self.state_callbacks:
                await self.state_callbacks["tool_message"](tool_message)
        
        print(f"========================================")
        
        # Extract assessment information if present
        if node_name == "assessment" and state.get("assessment_history"):
            assessment_history = state.get("assessment_history", [])
            if assessment_history and isinstance(assessment_history, list):
                # Extract metrics from the latest assessment entry
                latest_assessment = assessment_history[-1] if assessment_history else ""
                await self._extract_assessment_metrics(latest_assessment)
    
    async def _extract_assessment_metrics(self, assessment_text: str):
        """Extract assessment metrics from assessment text."""
        try:
            # Simple parsing of assessment metrics
            # In a real implementation, you might use regex or NLP to extract scores
            metrics = AssessmentMetrics()
            
            lines = assessment_text.split('\n')
            for line in lines:
                line = line.strip().lower()
                if 'active_vocabulary_usage:' in line:
                    score = self._extract_score(line)
                    metrics.active_vocabulary_usage = score
                elif 'comprehension_depth:' in line:
                    score = self._extract_score(line)
                    metrics.comprehension_depth = score
                elif 'contextual_application:' in line:
                    score = self._extract_score(line)
                    metrics.contextual_application = score
                elif 'retention_indicators:' in line:
                    score = self._extract_score(line)
                    metrics.retention_indicators = score
                elif 'overall' in line and 'mastery' in line:
                    score = self._extract_score(line)
                    metrics.overall_mastery = score
                elif 'next_steps' in line:
                    metrics.next_steps = line.split(':', 1)[1].strip() if ':' in line else ""
            
            # Notify about assessment update
            if "assessment_update" in self.state_callbacks:
                await self.state_callbacks["assessment_update"](metrics)
                
        except Exception as e:
            print(f"Error extracting assessment metrics: {e}")
    
    def _extract_score(self, line: str) -> Optional[int]:
        """Extract numeric score from assessment line."""
        import re
        match = re.search(r'\[score (\d)-5\]', line)
        if match:
            return int(match.group(1))
        
        # Try other patterns
        match = re.search(r'(\d)/5', line)
        if match:
            return int(match.group(1))
            
        return None
    
    async def send_user_message(self, message: str) -> bool:
        """Send user message to the conversation."""
        if not self.waiting_for_input:
            return False
        
        # Create user message
        user_message = Message(
            id=str(uuid.uuid4()),
            content=message,
            message_type=MessageType.USER,
            timestamp=datetime.now(),
            tool_calls=None
        )
        
        # Notify about user message
        if "user_message" in self.state_callbacks:
            await self.state_callbacks["user_message"](user_message)
        
        # Add to input queue
        await self.input_queue.put(message)
        self.waiting_for_input = False
        
        return True
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for state updates."""
        if event_type.startswith("tool_"):
            self.tool_callbacks[event_type] = callback
        else:
            self.state_callbacks[event_type] = callback
    
    async def get_current_state(self) -> Optional[StateInfo]:
        """Get current conversation state."""
        if self.current_state is None:
            return None
            
        return StateInfo(
            current_node="unknown",  # We'd need to track this better
            learning_goals=self.current_state.get("learning_goals", ""),
            active_cards=self.current_state.get("active_cards", ""),
            assessment_history=self.current_state.get("assessment_history", []),
            counter=self.current_state.get("counter", 0)
        )
    
    async def stop_conversation(self):
        """Stop the current conversation."""
        self.conversation_active = False
        
        # Clear any pending inputs
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    async def _notify_conversation_end(self):
        """Notify that conversation has ended."""
        if "conversation_end" in self.state_callbacks:
            await self.state_callbacks["conversation_end"]({"reason": "completed"})
    
    async def _notify_session_timeout(self):
        """Notify about session timeout."""
        if "conversation_end" in self.state_callbacks:
            await self.state_callbacks["conversation_end"]({"reason": "timeout"})
    
    async def _notify_error(self, error_message: str):
        """Notify about errors."""
        if "error" in self.state_callbacks:
            await self.state_callbacks["error"]({"message": error_message})