from typing import Annotated, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import InjectedToolCallId, tool
from basic_intent import classify_intent

llm = ChatOpenAI(
    model_name="uxly-model",
    base_url="http://0.0.0.0:4000",
    api_key="None",
)

def route_intent(
    state: MessagesState,
):
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state: {state}")
    intent, _ = classify_intent(ai_message.content)
    if intent != "product inquiry" and intent != "price inquiry":
        return "OTHER"
    return intent


def route_tools(
    state: MessagesState,
):
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END

@tool
def lookup_product_info(query: str) -> str:
    """Call to get information about a product."""
    result_str = llm.invoke("Answer this question no matter what: " + query).content
    return result_str


tools = [lookup_product_info]
llm_with_tools = llm.bind_tools(tools)


def product_chatbot(state: MessagesState):
    message = llm_with_tools.invoke(state["messages"])
    return {"messages": [message]}


def misc_chatbot(state: MessagesState):
    return {"messages": [HumanMessage(content="I can't help with that.")]}


graph_builder = StateGraph(MessagesState)

graph_builder.add_node("product_chatbot", product_chatbot)
graph_builder.add_node("misc_chatbot", misc_chatbot)

tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    START,
    route_intent,
    {
        "product inquiry": "product_chatbot",
        "price inquiry": "product_chatbot",
        "OTHER": "misc_chatbot",
    },
)

graph_builder.add_conditional_edges(
    "product_chatbot",
    route_tools,
    {
        "tools": "tools",
        END: END,
    },
)

graph_builder.add_edge("tools", "product_chatbot")
graph_builder.add_edge("misc_chatbot", END)

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

user_input = (
    "Tell me about the iPhone 13 Pro Max. What are the features and specifications?"
)
config = {"configurable": {"thread_id": "1"}, "recursion_limit": 150}

events = graph.stream(
    {"messages": [{"role": "user", "content": user_input}]},
    config,
    stream_mode="values",
)
for event in events:
    if "messages" in event:
        event["messages"][-1].pretty_print()
