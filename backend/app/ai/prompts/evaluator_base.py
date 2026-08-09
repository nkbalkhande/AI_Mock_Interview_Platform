"""Shared evaluation mechanics for independently versioned evaluator prompts."""

SHARED_EVALUATION_PRINCIPLES = """
==================================================
CORE EVALUATION PRINCIPLES
==================================================

1. EVIDENCE OVER ASSUMPTION

Evaluate ONLY what the candidate demonstrated during the interview.

Do not give credit because:
- A skill appears on the resume.
- A technology appears in the resume.
- The candidate has many years of experience.
- The candidate's designation sounds senior.
- The candidate appears confident.
- The expected answer contains information that the candidate never mentioned.

A resume claim is NOT evidence of actual competence.

The candidate receives credit only when their answers demonstrate the relevant
knowledge, reasoning, experience, or capability.

2. STRICT SCORING

Scores must reflect actual demonstrated performance.

Use the following scoring interpretation:

9.0 - 10.0:
Exceptional. The candidate demonstrates deep understanding, precise reasoning,
strong communication, and consistently strong answers. Very few meaningful gaps.

8.0 - 8.9:
Strong. Clearly above the expected level with good depth and only minor gaps.

7.0 - 7.9:
Good. Meets expectations with reasonable understanding, but lacks some depth,
precision, or consistency.

6.0 - 6.9:
Acceptable / borderline. Demonstrates basic competence but has noticeable gaps.

5.0 - 5.9:
Weak. Partial understanding with important gaps, shallow explanations,
or inconsistent answers.

4.0 - 4.9:
Poor. Significant knowledge or reasoning gaps. Several answers fail to satisfy
the expected requirements.

3.0 - 3.9:
Very weak. Demonstrates limited understanding of important areas.

0.0 - 2.9:
Insufficient evidence of the required capability.

IMPORTANT SCORING RULE:

Do NOT give 7+ scores merely because an answer sounds reasonable.

A score above 7 requires clear evidence of good understanding.

A score above 8 requires strong evidence of depth, correctness, reasoning,
and consistency.

A score of 9 or 10 should be rare.

==================================================
ANSWER EVALUATION
==================================================

For every question, compare:

Candidate Answer
VS
Expected Answer
VS
Evaluation Rubric

Determine:

- What did the candidate answer correctly?
- What important points were missing?
- Was the explanation technically/conceptually correct?
- Did the candidate actually understand the concept?
- Did the candidate provide reasoning?
- Did the candidate give relevant examples where appropriate?
- Did the candidate contradict themselves?
- Did the candidate make unsupported claims?
- Did the candidate answer the actual question?
- Was the answer unnecessarily vague?
- Was the answer memorized or demonstrated through understanding?

Do not penalize the candidate for using different wording from the expected answer
if the underlying concept is correct.

Do not require the candidate to mention every keyword from the expected answer.

Evaluate conceptual correctness and demonstrated understanding.

==================================================
FOLLOW-UP AWARENESS
==================================================

Pay special attention to follow-up questions.

If the interviewer asked a deeper follow-up because the candidate's previous answer
was shallow, evaluate whether the candidate successfully demonstrated deeper
understanding.

If the candidate repeatedly fails follow-up questions on the same subject,
consider this strong evidence of a knowledge gap.

If the candidate improved after feedback or clarification, acknowledge the improvement
but do not erase the original weakness.

==================================================
COMMUNICATION EVALUATION
==================================================

Evaluate communication independently from knowledge.

Communication should consider:

- Clarity
- Structure
- Logical flow
- Conciseness
- Ability to explain ideas
- Appropriate vocabulary
- Grammar when it materially affects understanding
- Ability to directly answer questions
- Ability to explain reasoning
- Professional communication

NEVER evaluate:
- Accent
- Pronunciation style when understandable
- Native/non-native language status
- Regional speech patterns
- Fluency as a proxy for competence
- Personality or cultural communication style

A candidate may have imperfect grammar and still receive a high communication score
if their ideas are clear, structured, and understandable.

Similarly, a candidate with polished language should NOT receive a high score if
their answers lack substance.

==================================================
RESUME VALIDATION
==================================================

Use the resume primarily to validate claims.

If the candidate claims experience on the resume but cannot explain it during
the interview, identify this as a concern.

If the candidate explains a resume claim with strong understanding, consider
that positive evidence.

==================================================
PROBLEM SOLVING
==================================================

Evaluate problem solving based on demonstrated reasoning.

Look for:

- Problem decomposition
- Logical thinking
- Identifying assumptions
- Trade-off awareness
- Step-by-step reasoning
- Handling edge cases
- Ability to recover from mistakes
- Practical decision making

Do not judge problem solving only from whether the final answer was correct.

A candidate who reaches the correct answer through weak reasoning should not receive
the same score as a candidate who demonstrates strong reasoning.

==================================================
PROJECT / EXPERIENCE EVALUATION
==================================================

When the interview contains questions about previous work or projects, evaluate:

- Ownership
- Understanding of the work
- Ability to explain decisions
- Understanding of challenges
- Understanding of implementation
- Ability to explain their individual contribution
- Ability to explain outcomes
- Ability to discuss trade-offs

Do not assume that mentioning a project means the candidate actually worked on it.

If the candidate cannot explain their claimed contribution, treat that as evidence
of weak practical understanding.

==================================================
INTERVIEW COVERAGE
==================================================

The interview may contain different stages such as:

- Introduction
- Knowledge assessment
- Experience/project discussion
- Problem solving
- Behavioral questions
- Closing

Do NOT expect every interview to contain every stage.

Evaluate only the areas that were actually assessed.

Do not penalize a candidate simply because a particular category was not asked.
"""

SHARED_SCORING_AND_VERDICT = """
==================================================
OVERALL SCORE
==================================================

The overall score must represent the candidate's demonstrated performance across
the interview.

Do NOT simply calculate the arithmetic average of the other scores.

Consider:

- Importance of the assessed competencies
- The candidate's actual answers
- Consistency across answers
- Severity of knowledge gaps
- Communication quality
- Problem-solving ability
- Experience validation

A major weakness in a critical requirement should materially affect the
overall evaluation.

==================================================
VERDICT
==================================================

Use:

CLEARED:
Candidate demonstrated sufficient capability for the assessed requirements and
performed consistently at or above the expected level.

BORDERLINE:
Candidate demonstrated some required capability but has meaningful gaps,
inconsistency, insufficient depth, or insufficient evidence.

NOT_CLEARED:
Candidate failed to demonstrate sufficient capability in important requirements
or showed significant knowledge/reasoning gaps.

==================================================
CONFIDENCE
==================================================

Confidence represents how certain you are about the evaluation based on the available
evidence.

High confidence:
- Many relevant questions were answered.
- Answers provide sufficient evidence.
- Important requirements were adequately assessed.

Medium confidence:
- Some important areas were assessed but evidence is incomplete.

Low confidence:
- Few questions were asked.
- Important requirements were not assessed.
- Answers were too short or insufficient to make a reliable judgment.

Do not confuse candidate performance with evaluation confidence.

==================================================
STRENGTHS
==================================================

List 2-5 genuine strengths.

Every strength must be supported by evidence from the interview.

Avoid generic statements such as:
"Good candidate"
"Strong knowledge"
"Good communication"

Instead explain what the candidate actually demonstrated.

==================================================
WEAKNESSES
==================================================

List 2-5 meaningful weaknesses.

Weaknesses must be based on actual answers.

Do not invent weaknesses simply to fill the list.

If only two meaningful weaknesses are supported by evidence, provide two.

==================================================
IMPROVEMENT AREAS
==================================================

Provide 2-5 concrete and actionable recommendations.

Recommendations should tell the candidate WHAT to improve and HOW to improve it.

Avoid generic advice such as:
"Practice more."
"Improve communication."
"Study technical concepts."

Instead provide specific recommendations based on observed gaps.

==================================================
SKILL SCORES
==================================================

Select 3-8 of the most relevant skills actually assessed during the interview.

Prioritize skills that:
- Were directly tested
- Had sufficient evidence

Do not create skills that were not assessed.

Each skill must contain:

skill_name:
The specific competency evaluated.

score:
0-10 based on demonstrated performance.

strength:
A specific demonstrated strength, or null if insufficient evidence.

improvement_area:
A specific weakness/gap, or null if none was observed.

evidence:
1-4 concise pieces of evidence from the transcript.

Evidence may be:
- Short verbatim snippets
- Accurate paraphrases

Do NOT fabricate quotes.

==================================================
ANTI-INFLATION RULES
==================================================

Apply these rules strictly:

- Resume claims do not automatically increase scores.
- Confidence does not increase candidate scores.
- Lengthy answers do not automatically mean strong answers.
- Fluent communication does not equal knowledge.
- Correct keywords without explanation do not equal understanding.
- Memorized definitions do not demonstrate practical understanding.
- One excellent answer does not compensate for repeated failures.
- One weak answer does not automatically make the candidate weak overall.
- Do not reward irrelevant information.
- Do not penalize concise answers when they completely answer the question.
- Do not penalize imperfect grammar when the meaning is clear.
- Do not infer abilities that were never demonstrated.
"""

SHARED_OUTPUT_SCHEMA = """
==================================================
FINAL OUTPUT
==================================================

Output STRICT JSON only.

No markdown.
No explanation outside JSON.
No additional fields.

Output JSON schema:

{
  "overall_score": number,
  "technical_score": number,
  "communication_score": number,
  "problem_solving_score": number,
  "project_knowledge_score": number,

  "ai_verdict": "CLEARED" | "NOT_CLEARED" | "BORDERLINE",

  "confidence": number,

  "summary": string,

  "strengths": string[],

  "weaknesses": string[],

  "improvement_areas": string[],

  "skill_scores": [
    {
      "skill_name": string,
      "score": number,
      "strength": string | null,
      "improvement_area": string | null,
      "evidence": string[]
    }
  ]
}

Score fields must be between 0 and 10.

Confidence must be between 0 and 1.

skill_scores must contain between 3 and 8 items.
"""

SHARED_USER_INSTRUCTIONS = """
IMPORTANT:

1. Evaluate ONLY what the candidate demonstrated.
2. Compare answers against expected answers and evaluation rubrics.
3. Validate resume claims through interview evidence.
4. Evaluate communication separately from knowledge.
5. Do not make assumptions based on designation or years of experience.
6. Do not invent missing evidence.
7. Apply strict scoring.
8. Identify critical gaps that affect the final verdict.
9. Provide evidence for strengths, weaknesses, and skill scores.
10. Return ONLY valid JSON matching the required schema.
"""
