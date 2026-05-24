# Minimal smoke tests — ensures pytest finds at least one test so CI doesn't exit code 5.
# Real integration tests go in test_api.py / test_inference.py etc.

def test_placeholder():
    """Placeholder so pytest always finds at least one test."""
    assert True
