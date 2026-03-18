"""
Unit tests for components/pii_eval/src/evaluate.py
All pure-logic functions — no mocking required.
"""
from evaluate import (
    _tokenise,
    build_bio_pairs,
    build_sample_log,
    collect_pii_labels,
    to_bio_sequence,
    token_pii_metrics,
    _make_predicates,
)


LABELS = {"PERSON", "EMAIL", "DATE"}


def make_predicates():
    return _make_predicates(LABELS)


class TestTokenise:
    def test_plain_text_splits_into_words(self):
        tokens = _tokenise("hello world foo")
        assert tokens == ["hello", "world", "foo"]

    def test_bracket_label_is_single_token(self):
        tokens = _tokenise("[PERSON]")
        assert tokens == ["[PERSON]"]

    def test_mixed_text_and_label(self):
        tokens = _tokenise("Hello [NAME] how are you")
        assert "[NAME]" in tokens
        assert "Hello" in tokens

    def test_multiple_labels_in_sentence(self):
        tokens = _tokenise("contact [EMAIL] or [PHONE] for info")
        assert "[EMAIL]" in tokens
        assert "[PHONE]" in tokens

    def test_empty_string_returns_empty_list(self):
        assert _tokenise("") == []

    def test_extra_whitespace_handled(self):
        tokens = _tokenise("  hello   world  ")
        assert "hello" in tokens
        assert "world" in tokens
        assert "" not in tokens

    def test_punctuation_stripped_from_plain_tokens(self):
        tokens = _tokenise("hello, world.")
        assert "" not in tokens


class TestCollectPiiLabels:
    def test_finds_single_label(self):
        labels = collect_pii_labels(["Hello [PERSON]"])
        assert "PERSON" in labels

    def test_finds_multiple_labels_across_strings(self):
        labels = collect_pii_labels(["[EMAIL] sent to [PERSON]", "call [PHONE]"])
        assert "EMAIL" in labels
        assert "PERSON" in labels
        assert "PHONE" in labels

    def test_deduplicates_labels(self):
        labels = collect_pii_labels(["[PERSON] met [PERSON]"])
        assert labels.count("PERSON") if isinstance(labels, list) else len([l for l in labels if l == "PERSON"]) == 1

    def test_none_entries_skipped(self):
        labels = collect_pii_labels([None, "[EMAIL]", None])
        assert "EMAIL" in labels

    def test_labels_uppercased(self):
        labels = collect_pii_labels(["[person]"])
        assert "PERSON" in labels

    def test_empty_list_returns_empty_set(self):
        assert collect_pii_labels([]) == set()


class TestToBioSequence:
    def test_bracket_label_gets_b_prefix(self):
        is_special, extract_label = make_predicates()
        tokens = ["[PERSON]"]
        tags = to_bio_sequence(tokens, is_special, extract_label)
        assert tags == ["B-PERSON"]

    def test_plain_token_gets_o_tag(self):
        is_special, extract_label = make_predicates()
        tokens = ["hello"]
        tags = to_bio_sequence(tokens, is_special, extract_label)
        assert tags == ["O"]

    def test_mixed_sequence_tagged_correctly(self):
        is_special, extract_label = make_predicates()
        tokens = ["hello", "[PERSON]", "called"]
        tags = to_bio_sequence(tokens, is_special, extract_label)
        assert tags == ["O", "B-PERSON", "O"]

    def test_unknown_label_gets_o_tag(self):
        is_special, extract_label = make_predicates()
        tokens = ["[UNKNOWN_ENTITY]"]
        tags = to_bio_sequence(tokens, is_special, extract_label)
        assert tags == ["O"]


class TestTokenPiiMetrics:
    def test_perfect_match_gives_precision_recall_one(self):
        outputs = ["Hello [PERSON]"]
        grounds = ["Hello [PERSON]"]
        metrics = token_pii_metrics(outputs, grounds, LABELS)
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0

    def test_all_missed_gives_recall_zero(self):
        outputs = ["Hello John"]
        grounds = ["Hello [PERSON]"]
        metrics = token_pii_metrics(outputs, grounds, LABELS)
        assert metrics["recall"] == 0.0
        assert metrics["fn"] > 0

    def test_false_positives_reduce_precision(self):
        outputs = ["[PERSON] [EMAIL] met [DATE]"]
        grounds = ["[PERSON] foo met bar"]
        metrics = token_pii_metrics(outputs, grounds, LABELS)
        assert metrics["fp"] > 0
        assert metrics["precision"] < 1.0

    def test_exact_match_rate_counted_correctly(self):
        outputs = ["Hello [PERSON]", "foo bar"]
        grounds = ["Hello [PERSON]", "foo bar"]
        metrics = token_pii_metrics(outputs, grounds, LABELS)
        assert metrics["exact_match_count"] == 2
        assert metrics["exact_match_rate"] == 1.0

    def test_partial_match_counted_when_some_tp(self):
        outputs = ["[PERSON] and [EMAIL]"]
        grounds = ["[PERSON] and [DATE]"]
        metrics = token_pii_metrics(outputs, grounds, LABELS)
        assert metrics["partial_match_count"] >= 1

    def test_false_negative_rate_formula(self):
        outputs = ["Hello John"]
        grounds = ["Hello [PERSON]"]
        metrics = token_pii_metrics(outputs, grounds, LABELS)
        tp = metrics["tp"]
        fn = metrics["fn"]
        expected_fnr = fn / (tp + fn) if (tp + fn) else 0.0
        assert abs(metrics["false_negative_rate"] - expected_fnr) < 1e-9

    def test_none_outputs_excluded_from_valid_count(self):
        outputs = [None, "[PERSON]"]
        grounds = ["[PERSON]", "[PERSON]"]
        metrics = token_pii_metrics(outputs, grounds, LABELS)
        assert metrics["n_valid"] == 1


class TestBuildBioPairs:
    def test_output_lists_same_length(self):
        outputs = ["[PERSON] called"]
        grounds = ["[PERSON] called [DATE]"]
        pred, gold = build_bio_pairs(outputs, grounds, LABELS)
        assert len(pred[0]) == len(gold[0])

    def test_none_output_skipped(self):
        outputs = [None, "[PERSON]"]
        grounds = ["[PERSON]", "[PERSON]"]
        pred, gold = build_bio_pairs(outputs, grounds, LABELS)
        assert len(pred) == 1
        assert len(gold) == 1

    def test_correct_label_in_pred_tags(self):
        outputs = ["[PERSON]"]
        grounds = ["[PERSON]"]
        pred, gold = build_bio_pairs(outputs, grounds, LABELS)
        assert "B-PERSON" in pred[0]
        assert "B-PERSON" in gold[0]


class TestBuildSampleLog:
    def test_perfect_match_gives_match_result(self):
        df = build_sample_log(
            source_texts=["John called"],
            grounds=["[PERSON] called"],
            outputs=["[PERSON] called"],
            special_labels=LABELS,
            model="test-model",
            dataset_name="test",
            source_col="source_text",
            gt_col="masked_text",
        )
        assert df.iloc[0]["result"] == "match"

    def test_missed_pii_gives_miss_result(self):
        df = build_sample_log(
            source_texts=["John called"],
            grounds=["[PERSON] called"],
            outputs=["John called"],
            special_labels=LABELS,
            model="test-model",
            dataset_name="test",
            source_col="source_text",
            gt_col="masked_text",
        )
        assert df.iloc[0]["result"] == "miss"

    def test_none_output_gives_error_result(self):
        df = build_sample_log(
            source_texts=["John called"],
            grounds=["[PERSON] called"],
            outputs=[None],
            special_labels=LABELS,
            model="test-model",
            dataset_name="test",
            source_col="source_text",
            gt_col="masked_text",
        )
        assert df.iloc[0]["result"] == "error"

    def test_fn_count_zero_on_perfect_match(self):
        df = build_sample_log(
            source_texts=["text"],
            grounds=["[PERSON]"],
            outputs=["[PERSON]"],
            special_labels=LABELS,
            model="model",
            dataset_name="ds",
            source_col="src",
            gt_col="gt",
        )
        assert df.iloc[0]["fn_count"] == 0

    def test_fn_count_positive_on_miss(self):
        df = build_sample_log(
            source_texts=["text"],
            grounds=["[PERSON] and [EMAIL]"],
            outputs=["John and email@test.com"],
            special_labels=LABELS,
            model="model",
            dataset_name="ds",
            source_col="src",
            gt_col="gt",
        )
        assert df.iloc[0]["fn_count"] > 0

    def test_dataframe_contains_required_columns(self):
        df = build_sample_log(
            source_texts=["text"],
            grounds=["[PERSON]"],
            outputs=["[PERSON]"],
            special_labels=LABELS,
            model="model",
            dataset_name="ds",
            source_col="src",
            gt_col="gt",
        )
        for col in ["model", "result", "fn_count", "source_text", "ground_truth", "model_output"]:
            assert col in df.columns
