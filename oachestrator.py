
from dotenv import load_dotenv

import llama_index
from llama_index.core import download_loader
from llama_index.core import VectorStoreIndex #ServiceContext
# from llama_index.core import ServiceContext
from llama_index.llms.gemini import Gemini
# from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings

load_dotenv()

URL = "https://en.wikipedia.org/wiki/Abraham_Lincoln"


BeautifulSoupWebReader = download_loader("BeautifulSoupWebReader")
loader = BeautifulSoupWebReader()
documents = loader.load_data(urls=[URL])

# service_context = ServiceContext.from_defaults(llm=Gemini())
Settings.llm = Gemini()
# Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)
Settings.num_output = 512
Settings.context_window = 3900

index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(llm=Gemini)

query = "What is this web page about?"
response = query_engine.query(query)
print(f"RESPONSE:\n{response}")