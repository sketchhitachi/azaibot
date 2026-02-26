import requests

def free_ai(prompt):
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium",
            json={"inputs": prompt},
            timeout=10
        )
        return response.json()[0]["generated_text"]
    except:
        return "🤖 AI busy..."
