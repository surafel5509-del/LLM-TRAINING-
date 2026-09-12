# Testing

`backend/tests/test_training.py` contains a deterministic ML proof test. It constructs an MLP, computes a real cross-entropy loss, runs backpropagation and an optimizer step, and asserts that at least one weight tensor changes.

The second test verifies deterministic data splitting and target encoding.

Recommended next additions are API integration tests, a subprocess training smoke test, checkpoint restoration tests, and Playwright end-to-end coverage. They are not claimed as complete until executed in CI.
