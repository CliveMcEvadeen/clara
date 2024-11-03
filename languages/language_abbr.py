import fasttext

# Load the pre-trained model
model = fasttext.load_model('lid.176.bin')

# Sample texts for language identification
texts = [
    "Hello, how are you?",
    "Oli otya?",
    "Bonjour, comment ça va?",
    "Ciao, come stai?"
]

# Identify the language of each text
for text in texts:
    # The model returns the language and confidence score
    predicted = model.predict(text)
    language_code = predicted[0][0].replace("__label__", "")  # Clean up the output
    confidence_score = predicted[1][0]
    
    print(f"Text: '{text}' | Detected Language: '{language_code}' | Confidence: {confidence_score:.2f}")
