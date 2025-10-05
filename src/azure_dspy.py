import os
import dspy
from app.llm.signatures import UserMessageIntentSignature

api_key="0ea6f9a16cc841c3ae3cdfa50c0c1fc5"
api_base="https://yoov-openai-east-us-2.openai.azure.com/"


lm = dspy.LM("azure/gpt-4.1-mini",
    api_key=api_key,
    api_base=api_base,
    api_version="2025-01-01-preview",
    stream=False)

dspy.configure(lm=lm)

predict = dspy.Predict(UserMessageIntentSignature)

intent = predict(user_message="how are you")

print(intent)