import os
import dspy


api_key="0ea6f9a16cc841c3ae3cdfa50c0c1fc5"
api_base="https://yoov-openai-east-us-2.openai.azure.com/"


lm = dspy.LM("azure/gpt-4.1-mini",
    api_key=api_key,
    api_base=api_base,
    api_version="2025-01-01-preview",
    stream=False)

dspy.configure(lm=lm)

class BasicQA(dspy.Signature):
    """Answer questions with short factoid answers."""

    question: str = dspy.InputField()
    answer: str = dspy.OutputField(desc="often between 1 and 5 words")



# intent = dspy.ChainOfThought("input -> output")(input="how are you")
# print(f"Token usage: {intent.get_lm_usage()}", intent)

dspy.settings.configure(track_usage=True)


# result = dspy.ChainOfThought(BasicQA)(question="What is 2+2?")
# print(f"Token usage: {result.get_lm_usage()}")

pot = dspy.ProgramOfThought(BasicQA)

dspy.configure(track_usage=True)

question = 'What is the probability of get 6 correct number in total 45 numbers? after each draw, the 45 will become 44 and so on.'
result = pot(question=question)

print(f"Question: {question}")
print(f"Final Predicted Answer (after ProgramOfThought process): {result.answer}")
print(f"Result: {result}")
print(dspy.inspect_history())
print(f"Token usage: {result.get_lm_usage()}")