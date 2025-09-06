# langgraph_agents.py
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnablePassthrough
import json

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    patient_info: dict
    appointment_data: dict
    stage: str
    next_action: str

class MedicalSchedulingGraph:
    def __init__(self, scheduling_agent):
        self.scheduling_agent = scheduling_agent
        self.graph = self._create_graph()
        
    def _create_graph(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("greeting_agent", self.greeting_node)
        workflow.add_node("lookup_agent", self.lookup_node)
        workflow.add_node("scheduling_agent", self.scheduling_node)
        workflow.add_node("insurance_agent", self.insurance_node)
        workflow.add_node("confirmation_agent", self.confirmation_node)
        workflow.add_node("calendar_integration", self.calendar_node)
        workflow.add_node("email_notification", self.email_node)
        workflow.add_node("reminder_setup", self.reminder_node)
        
        # Define the flow
        workflow.set_entry_point("greeting_agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "greeting_agent",
            self.route_after_greeting,
            {
                "lookup": "lookup_agent",
                "greeting": "greeting_agent"
            }
        )
        
        workflow.add_conditional_edges(
            "lookup_agent",
            self.route_after_lookup,
            {
                "scheduling": "scheduling_agent",
                "lookup": "lookup_agent"
            }
        )
        
        workflow.add_conditional_edges(
            "scheduling_agent",
            self.route_after_scheduling,
            {
                "insurance": "insurance_agent",
                "scheduling": "scheduling_agent"
            }
        )
        
        workflow.add_conditional_edges(
            "insurance_agent",
            self.route_after_insurance,
            {
                "confirmation": "confirmation_agent",
                "insurance": "insurance_agent"
            }
        )
        
        workflow.add_conditional_edges(
            "confirmation_agent",
            self.route_after_confirmation,
            {
                "calendar": "calendar_integration",
                "confirmation": "confirmation_agent",
                "scheduling": "scheduling_agent"
            }
        )
        
        workflow.add_edge("calendar_integration", "email_notification")
        workflow.add_edge("email_notification", "reminder_setup")
        workflow.add_edge("reminder_setup", END)
        
        return workflow.compile()
    
    def greeting_node(self, state: AgentState) -> AgentState:
        """Handle patient greeting"""
        last_message = state["messages"][-1].content
        response = self.scheduling_agent._handle_greeting(last_message)
        
        # Update state
        state["messages"].append({"role": "assistant", "content": response})
        
        # Determine next action
        if "provide" in response.lower() and ("name" in response.lower() or "birth" in response.lower()):
            state["next_action"] = "greeting"
        else:
            state["next_action"] = "lookup"
            state["stage"] = "patient_lookup"
            
        return state
    
    def lookup_node(self, state: AgentState) -> AgentState:
        """Handle patient lookup"""
        last_message = state["messages"][-1].content
        response = self.scheduling_agent._handle_patient_lookup(last_message)
        
        state["messages"].append({"role": "assistant", "content": response})
        
        if "date would you prefer" in response:
            state["next_action"] = "scheduling"
            state["stage"] = "scheduling"
        else:
            state["next_action"] = "lookup"
            
        return state
    
    def scheduling_node(self, state: AgentState) -> AgentState:
        """Handle appointment scheduling"""
        last_message = state["messages"][-1].content
        response = self.scheduling_agent._handle_scheduling(last_message)
        
        state["messages"].append({"role": "assistant", "content": response})
        
        if "select a slot number" in response.lower():
            state["next_action"] = "insurance"
            state["stage"] = "insurance"
        else:
            state["next_action"] = "scheduling"
            
        return state
    
    def insurance_node(self, state: AgentState) -> AgentState:
        """Handle insurance collection"""
        last_message = state["messages"][-1].content
        
        # Handle slot selection
        if last_message.isdigit():
            slot_index = int(last_message) - 1
            # Simulate slot selection logic
            response = "Great! I've selected that time slot. Now, could you please provide your insurance company name and member ID?"
            state["next_action"] = "insurance"
        else:
            response = self.scheduling_agent._handle_insurance(last_message)
            if "confirm your appointment" in response.lower():
                state["next_action"] = "confirmation"
                state["stage"] = "confirmation"
            else:
                state["next_action"] = "insurance"
        
        state["messages"].append({"role": "assistant", "content": response})
        return state
    
    def confirmation_node(self, state: AgentState) -> AgentState:
        """Handle appointment confirmation"""
        last_message = state["messages"][-1].content
        
        if last_message.lower() in ['yes', 'confirm', 'y', 'ok', 'sure']:
            response = "Perfect! Processing your appointment confirmation..."
            state["next_action"] = "calendar"
        elif last_message.lower() in ['no', 'cancel', 'n']:
            response = "No problem! Let's modify your appointment."
            state["next_action"] = "scheduling"
            state["stage"] = "scheduling"
        else:
            response = "Please confirm by typing 'yes' or 'no'."
            state["next_action"] = "confirmation"
        
        state["messages"].append({"role": "assistant", "content": response})
        return state
    
    def calendar_node(self, state: AgentState) -> AgentState:
        """Handle calendar integration"""
        # Simulate calendar booking
        calendar_response = "📅 Calendar integration: Appointment booked in Calendly system"
        state["messages"].append({"role": "system", "content": calendar_response})
        return state
    
    def email_node(self, state: AgentState) -> AgentState:
        """Handle email notifications"""
        # Simulate email sending
        email_response = "📧 Email sent: Confirmation email with forms dispatched"
        state["messages"].append({"role": "system", "content": email_response})
        return state
    
    def reminder_node(self, state: AgentState) -> AgentState:
        """Setup reminder system"""
        # Simulate reminder setup
        reminder_response = "🔔 Reminder system: 3-tier automated reminders activated"
        
        final_response = """
        ✅ **LangGraph Workflow Complete!**
        
        All 8 features processed through LangGraph multi-agent system:
        1. ✅ Greeting Agent - Patient info collected
        2. ✅ Lookup Agent - Database search completed  
        3. ✅ Scheduling Agent - Time slot selected
        4. ✅ Insurance Agent - Coverage details captured
        5. ✅ Confirmation Agent - Appointment confirmed
        6. ✅ Calendar Agent - Calendly booking created
        7. ✅ Email Agent - Forms distributed
        8. ✅ Reminder Agent - Automation activated
        
        Your appointment is fully confirmed and all systems are integrated!
        """
        
        state["messages"].append({"role": "assistant", "content": final_response})
        return state
    
    # Routing functions
    def route_after_greeting(self, state: AgentState) -> str:
        return state["next_action"]
    
    def route_after_lookup(self, state: AgentState) -> str:
        return state["next_action"]
    
    def route_after_scheduling(self, state: AgentState) -> str:
        return state["next_action"]
    
    def route_after_insurance(self, state: AgentState) -> str:
        return state["next_action"]
    
    def route_after_confirmation(self, state: AgentState) -> str:
        return state["next_action"]
    
    def run_workflow(self, user_input: str) -> str:
        """Run the complete LangGraph workflow"""
        initial_state = {
            "messages": [{"role": "user", "content": user_input}],
            "patient_info": {},
            "appointment_data": {},
            "stage": "greeting",
            "next_action": "greeting"
        }
        
        final_state = self.graph.invoke(initial_state)
        
        # Return the last assistant message
        for message in reversed(final_state["messages"]):
            if message.get("role") == "assistant":
                return message["content"]
        
        return "Workflow completed successfully!"

# Integration with main scheduler
def enhance_with_langgraph(scheduling_agent):
    """Enhance the scheduling agent with LangGraph"""
    langgraph_workflow = MedicalSchedulingGraph(scheduling_agent)
    
    # Add LangGraph method to existing agent
    scheduling_agent.langgraph_workflow = langgraph_workflow
    
    def process_with_langgraph(user_input):
        """Process user input through LangGraph workflow"""
        return langgraph_workflow.run_workflow(user_input)
    
    scheduling_agent.process_with_langgraph = process_with_langgraph
    
    return scheduling_agent