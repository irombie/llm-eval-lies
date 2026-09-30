"""
Example Jev questions from the talk, as DeepEval JevEval metrics.

Untested sketch: written against the DeepEval JevEval docs
(https://deepeval.com/docs/metrics-jev-eval). Check it against the
current docs before relying on it.

Setup:
    pip install deepeval typesafe-sdk
    export TYPESAFE_API_KEY=...
Run:
    python jev_examples.py
"""

from deepeval import evaluate
from deepeval.metrics import JevEval
from deepeval.metrics.jev_eval import Choice, Noul, Score
from deepeval.test_case import LLMTestCase, SingleTurnParams

# Noul: a yes/no check. Score: a degree, levels listed WORST FIRST.
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

# Choice: distinct behaviors. Credit None means "does not apply".
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

if __name__ == "__main__":
    case = LLMTestCase(
        input="İade süresi kaç gün?",
        actual_output="Ürünü teslim aldıktan sonra 14 gün içinde iade edebilirsiniz.",
        retrieval_context=["İade süresi, teslimattan itibaren 14 gündür."],
    )
    evaluate(test_cases=[case], metrics=[answer_quality])
