from llama_index.llms.gemini import Gemini


import os

GOOGLE_API_KEY = "AIzaSyBIo9a4ww84drZw6mO3rL7Onn0JuuGj_7M"  # add your GOOGLE API key here
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

luganda_data="lukozesebwa nnyo mu masekkati ga Yuganda. Lwe lulimi olukozesebwa okusinga mu nsi ya Yuganda. Olugaganda luva ku linnya ly'Abaganda, abalwogera okuva edda nnyo. Olw'okuba ebibuga ebikulu ebya Yuganda mu myaka gyonna bisangibwa mu Buganda, olulimi lwayambuka nnyo mu byetaagisa mu Yuganda yonna, kuba kati lukozesebwa nnyo mu by'obusuubuzi mu maduuka, ne mu butale obw'enjawulo mu Yuganda., which language is that"

resp = Gemini().complete(luganda_data)
print(resp)
