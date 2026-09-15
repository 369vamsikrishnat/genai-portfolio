from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

client = genai.Client()

models = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

print("\nTesting Gemini models...\n")

for model in models:
    try:
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: OK",
        )

        print(f"{model:<30} ✅ WORKING")

    except errors.APIError as error:
        print(
            f"{model:<30} ❌ "
            f"{error.code} {error.status}"
        )

    except Exception as error:
        print(
            f"{model:<30} ❌ "
            f"{type(error).__name__}: {error}"
        )