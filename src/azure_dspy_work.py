import os
import dspy

api_key="0ea6f9a16cc841c3ae3cdfa50c0c1fc5"
api_base="https://yoov-openai-east-us-2.openai.azure.com/"


lm = dspy.LM("azure/gpt-4.1-mini",
    api_key=api_key,
    api_base=api_base,
    api_version="2025-01-01-preview",
    stream=False)

# result = lm("Say this is a test!", temperature=0.7)  # => ['This is a test!']
#
# print(result)

dspy.configure(lm=lm)

predictor = dspy.Predict("input -> output")

intent = predictor(input="how are you")

print(intent)