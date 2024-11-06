from llama_index.llms.gemini import Gemini

llm = Gemini()
resp = llm.stream_complete(
   "narrate for me a story"
)

for r in resp:
    print(r.text, end="")


def data(data: str):
   pass