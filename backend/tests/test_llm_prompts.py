from anneal.llm.prompts import build_challenge_prompt, build_verdict_prompt


class TestBuildChallengePrompt:
    def test_challenge_prompt_returns_tuple_of_strings(self):
        system, user = build_challenge_prompt("claim", "context")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_challenge_prompt_contains_claim_and_context(self):
        system, user = build_challenge_prompt("X improves Y", "some background")
        assert "X improves Y" in user
        assert "some background" in user

    def test_challenge_prompt_system_contains_json_instruction(self):
        system, user = build_challenge_prompt("claim", "ctx")
        assert "JSON" in system


class TestBuildVerdictPrompt:
    def test_verdict_prompt_returns_tuple_of_strings(self):
        system, user = build_verdict_prompt("claim", "question", "answer")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_verdict_prompt_contains_all_inputs(self):
        system, user = build_verdict_prompt("my claim", "my question", "my answer")
        assert "my claim" in user
        assert "my question" in user
        assert "my answer" in user

    def test_verdict_prompt_system_contains_json_instruction(self):
        system, user = build_verdict_prompt("c", "q", "a")
        assert "JSON" in system
