"""
Example Jev questions from the talk, as DeepEval JevEval metrics.

Jev answers typed questions (Noul, Score, Choice) with probabilities instead
of generating text, so a metric is just the list of questions you want asked
about each test case. Docs: https://deepeval.com/docs/metrics-jev-eval

Checked against deepeval 4.3.2 and typesafe-sdk 0.7.5: the metrics and test
cases below build cleanly. Scoring calls the Jev API, so it needs a key.
Jev is in early access; check the docs if a newer release changes the API.

Setup:
    pip install deepeval typesafe-sdk
    export TYPESAFE_API_KEY=...
Run:
    python jev_examples.py
"""

import os
import sys

from deepeval import evaluate
from deepeval.metrics import JevEval
from deepeval.metrics.jev_eval import Choice, Noul, Score
from deepeval.test_case import LLMTestCase, SingleTurnParams, ToolCall


def build_metrics():
    # Noul: a yes/no check. Score: a degree, levels listed WORST FIRST
    # (the first level maps to 0, the last to 1).
    answer_quality = JevEval(
        name="Answer Quality (Turkish RAG)",
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.RETRIEVAL_CONTEXT,  # Jev only sees fields listed here
        ],
        questions=[
            Noul("Every fact in actual_output appears in retrieval_context.", weight=2),
            Noul("actual_output is written entirely in Turkish."),
            Score(
                "How completely does actual_output address input?",
                levels=["Does not answer", "Partly answers", "Mostly answers", "Fully answers"],
            ),
        ],
    )

    # Choice: distinct behaviors, each with a credit from 0 to 1.
    # Credit None means "does not apply": if those options hold most of the
    # probability, the question is dropped for that test case.
    tool_error_handling = JevEval(
        name="Tool Error Handling",
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.TOOLS_CALLED],
        questions=[
            Choice(
                "What did actual_output do when a call in tools_called failed?",
                options={
                    "retried_with_fixed_input": 1.0,
                    "told_the_user": 1.0,
                    "invented_a_result": 0.0,
                    "no_tool_failed": None,
                },
            ),
        ],
    )
    return answer_quality, tool_error_handling


def build_cases():
    rag_case = LLMTestCase(
        input="İade süresi kaç gün?",
        actual_output="Ürünü teslim aldıktan sonra 14 gün içinde iade edebilirsiniz.",
        retrieval_context=["İade süresi, teslimattan itibaren 14 gündür."],
    )
    # The tool failed and the agent made up an answer: this should score 0.
    tool_case = LLMTestCase(
        input="What is the status of order 1042?",
        actual_output="Your order 1042 shipped yesterday and arrives Friday.",
        tools_called=[
            ToolCall(
                name="get_order_status",
                input_parameters={"order_id": "1042"},
                output={"error": "503 Service Unavailable"},
            ),
        ],
    )
    return rag_case, tool_case


if __name__ == "__main__":
    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("Set TYPESAFE_API_KEY first (Jev scores the test cases). See the docstring.")
    answer_quality, tool_error_handling = build_metrics()
    rag_case, tool_case = build_cases()
    evaluate(test_cases=[rag_case], metrics=[answer_quality])
    evaluate(test_cases=[tool_case], metrics=[tool_error_handling])
