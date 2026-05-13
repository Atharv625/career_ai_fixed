import google.generativeai as genai

client = genai.Client(api_key="AIzaSyAqaq0-8Y-raKOMn4UeEpo6vTZurbs3I0c")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="hello"
)

print(response.text)