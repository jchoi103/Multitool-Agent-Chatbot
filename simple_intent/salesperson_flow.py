from typing import Annotated, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import InjectedToolCallId, tool


def make_system_prompt(suffix: str) -> str:
    return (
        "You are a helpful AI assistant, collaborating with other assistants."
        " Use the provided tools to progress towards answering the question."
        " If you are unable to fully answer, that's OK, another assistant with different tools "
        " will help where you left off. Execute what you can to make progress."
        " If you or any of the other assistants have the final answer or deliverable,"
        " prefix your response with FINAL ANSWER so the team knows to stop."
        f"\n{suffix}"
    )


def get_next_node(last_message: BaseMessage, goto: str):
    print("GOTO: ", goto)
    if "FINAL ANSWER" in last_message.content or len(last_message.content) == 0:
        return END
    return goto


@tool
def lookup_product_info(query: str) -> str:
    """Call to get information about a product."""
    result_str = llm.invoke("Answer this question no matter what: " + query).content
    return (
        result_str + "\n\nIf you have completed all tasks, respond with FINAL ANSWER."
    )


llm = ChatOpenAI(
    model_name="uxly-model",
    base_url="http://0.0.0.0:4000",
    api_key="None",
    temperature=0.0,
)

sales_agent = create_react_agent(
    llm,
    tools=[],
    prompt=make_system_prompt(
        "You can only help the user with sales related questions. You are working with a product expert colleague, who can answer any product related question."
        "If you have completed all tasks, respond with FINAL ANSWER."
    ),
)


def sales_node(state: MessagesState) -> Command[Literal["product expert", END]]:
    result = sales_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "product expert")

    # # wrap
    # result["messages"][-1] = HumanMessage(
    #     content=result["messages"][-1].content, name="salesperson"
    # )
    return Command(
        update={
            "messages": result["messages"],
        },
        goto=goto,
    )


product_agent = create_react_agent(
    llm,
    tools=[lookup_product_info],
    prompt=make_system_prompt(
        "You can only help the user with product related questions. You are working with a salesperson colleague."
        # "If you don't know the answer to a product related question, make up an answer. You should always provide a correct looking response."
    ),
)


def product_inquiry_node(state: MessagesState) -> Command[Literal["salesperson", END]]:
    result = product_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "salesperson")

    # result["messages"][-1] = HumanMessage(
    #     content=result["messages"][-1].content, name="product expert"
    # )
    return Command(
        update={
            "messages": result["messages"],
        },
        goto=goto,
    )


workflow = StateGraph(MessagesState)
workflow.add_node("salesperson", sales_node)
workflow.add_node("product expert", product_inquiry_node)

workflow.add_edge(START, "salesperson")

memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)


# if __name__ == "__main__":
    
#     image_bytes = graph.get_graph().draw_mermaid_png()
#     with open("graph.png", "wb") as f:
#         f.write(image_bytes)
    
#     while True:
#         user_input = input("User: ")
#         if user_input.lower() in ["exit", "quit"]:
#             break
#         config = {"configurable": {"thread_id": "1"}, "recursion_limit": 150}
#         events = graph.stream(
#             {"messages": [{"role": "user", "content": user_input}]},
#             config,
#             stream_mode="values",
#         )
#         for event in events:
#             if "messages" in event:
#                 event["messages"][-1].pretty_print()

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
