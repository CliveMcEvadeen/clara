import os
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.prompts import PromptTemplate
from llama_index.llms.gemini import Gemini
from llama_index.postprocessor.colbert_rerank import ColbertRerank
from typing import Any, Dict, List, Optional
from llama_index.core.bridge.pydantic import Field
from llama_index.core.llms import ChatMessage
from llama_index.core.query_pipeline import CustomQueryComponent
from llama_index.core.schema import NodeWithScore
from llama_index.readers.web import BeautifulSoupWebReader
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.core.query_pipeline import QueryPipeline, InputComponent, ArgPackComponent

# Replace with your actual API key
GOOGLE_API_KEY = "AIzaSyAMZy8kZR1iMLbE0h_Gc-sZEqAnYxuKzcc"

# Step 1: Load and Prepare Documents
def load_documents():
    reader = BeautifulSoupWebReader()
    documents = reader.load_data(["https://docs.llamaindex.ai/en/stable/module_guides/querying/structured_outputs/output_parser/"])
    lines = documents[0].text.split("\n")
    fixed_lines = [lines[0]]
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "" and lines[idx - 1].strip() == "":
            continue
        fixed_lines.append(lines[idx])
    documents[0].text = "\n".join(fixed_lines)
    return documents

documents = load_documents()

# Step 2: Initialize Embeddings and Index
model_name = "models/embedding-001"
index = VectorStoreIndex.from_documents(
    documents,
    embed_model=GeminiEmbedding(model_name=model_name, api_key=GOOGLE_API_KEY, title="this is a document")
)

# Step 3: Define Pipeline Components
input_component = InputComponent()

rewrite_template = PromptTemplate(
    "Please write a query to a semantic search engine using the current conversation.\n\n"
    "{chat_history_str}\n\nLatest message: {query_str}\nQuery:\n"
)

llm = Gemini()
retriever = index.as_retriever(similarity_top_k=1)  # Top 1 result for a single response
reranker = ColbertRerank(top_n=1)  # Top 1 reranked result

# Define context prompt for generating responses
DEFAULT_CONTEXT_PROMPT = (
    "Here is some context that may be relevant:\n"
    "-----\n{node_context}\n-----\n"
    "Please write a response to the following question, using the above context:\n"
    "{query_str}\n"
)

class ResponseWithChatHistory(CustomQueryComponent):
    llm: Gemini = Field(..., description="GEMINI LLM")
    system_prompt: Optional[str] = Field(default=None, description="System prompt to use for the LLM")
    context_prompt: str = Field(default=DEFAULT_CONTEXT_PROMPT, description="Context prompt to use for the LLM")

    def _validate_component_inputs(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required inputs are provided for the component."""
        return input

    @property
    def _input_keys(self) -> set:
        return {"chat_history", "nodes", "query_str"}

    @property
    def _output_keys(self) -> set:
        return {"response"}

    def _prepare_context(self, chat_history: List[ChatMessage], nodes: List[NodeWithScore], query_str: str) -> List[ChatMessage]:
        """Prepare the context by formatting node contents and appending to chat history."""
        node_context = ""
        for idx, node in enumerate(nodes):
            node_text = node.get_content(metadata_mode="llm")
            node_context += f"Context Chunk {idx}:\n{node_text}\n\n"

        formatted_context = self.context_prompt.format(node_context=node_context, query_str=query_str)
        user_message = ChatMessage(role="user", content=formatted_context)
        chat_history.append(user_message)

        if self.system_prompt:
            chat_history.insert(0, ChatMessage(role="system", content=self.system_prompt))

        return chat_history

    def _run_component(self, **kwargs) -> Dict[str, Any]:
        """Run the component to generate a response."""
        chat_history = kwargs["chat_history"]
        nodes = kwargs["nodes"]
        query_str = kwargs["query_str"]

        prepared_context = self._prepare_context(chat_history, nodes, query_str)
        response = self.llm.chat(prepared_context)
        return {"response": response.message}

    async def _arun_component(self, **kwargs: Any) -> Dict[str, Any]:
        """Asynchronous version of the run component."""
        chat_history = kwargs["chat_history"]
        nodes = kwargs["nodes"]
        query_str = kwargs["query_str"]

        prepared_context = self._prepare_context(chat_history, nodes, query_str)
        response = await self.llm.achat(prepared_context)
        return {"response": response.message}

response_component = ResponseWithChatHistory(
    llm=llm,
    system_prompt=(
        "You are a Q&A system. You will be provided with the previous chat history, "
        "as well as possibly relevant context, to assist in answering a user message."
    ),
)

# Step 4: Build the Query Pipeline
pipeline = QueryPipeline(
    modules={
        "input": input_component,
        "rewrite_template": rewrite_template,
        "llm": llm,
        "rewrite_retriever": retriever,
        "query_retriever": retriever,
        "join": ArgPackComponent(),
        "response_component": response_component,
    },
    verbose=False,
)

pipeline.add_link("input", "rewrite_template", src_key="query_str", dest_key="query_str")
pipeline.add_link("input", "rewrite_template", src_key="chat_history_str", dest_key="chat_history_str")
pipeline.add_link("rewrite_template", "llm")
pipeline.add_link("llm", "rewrite_retriever")
pipeline.add_link("input", "query_retriever", src_key="query_str")
pipeline.add_link("rewrite_retriever", "join", dest_key="rewrite_nodes")
pipeline.add_link("query_retriever", "join", dest_key="query_nodes")
pipeline.add_link("input", "response_component", src_key="query_str", dest_key="query_str")
pipeline.add_link("input", "response_component", src_key="chat_history", dest_key="chat_history")

# Memory buffer to store chat history
pipeline_memory = ChatMemoryBuffer.from_defaults(token_limit=8000)

# Step 5: Define Chat Pipeline Function
def run_chat_pipeline(message: str):
    try:
        # Retrieve chat history from memory
        chat_history = pipeline_memory.get()
        chat_history_str = "\n".join([str(x) for x in chat_history])

        # Run pipeline to get response
        response_output = pipeline.run(
            query_str=message,
            chat_history=chat_history,
            chat_history_str=chat_history_str,
        )

        # Extract and print single response
        response_text = response_output["response"]
        
        # Store messages in chat history memory
        user_msg = ChatMessage(role="user", content=message)
        pipeline_memory.put(user_msg)
        print(str(user_msg))

        ai_msg = ChatMessage(role="assistant", content=response_text)
        pipeline_memory.put(ai_msg)
        print(str(ai_msg))  # Output response

        return ai_msg.content

    except Exception as e:
        print(f"Error in chat pipeline: {str(e)}")
        return f"An error occurred: {str(e)}"

# Optional: Function to clear chat memory
def clear_chat_memory():
    pipeline_memory.reset()

# Step 6: Run Chat Session
if __name__ == "__main__":
    user_inputs = [
        "Hello!",
        "How does tool-use work with Claude-3?",
        "What models support it?",
        "Thanks, that's what I needed to know!",
    ]
    try:
        for msg in user_inputs:
            run_chat_pipeline(msg)
    except KeyboardInterrupt:
        print("\nChat session terminated by user.")
    finally:
        # Clear memory when done
        clear_chat_memory()
