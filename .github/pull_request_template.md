## What this changes

<!-- One paragraph. What problem does it solve, and for whom? -->

## How it was verified

<!-- Paste the commands you ran and the output you got. "Tested locally" alone is not enough. -->

```
$ 
```

- [ ] `.venv/bin/python -m unittest tests_gt.py` passes
- [ ] `.venv/bin/python test_bridge_lua.py` passes (required if `bridge.lua` changed)
- [ ] the changed tool was called against a real device and the output is pasted above

## Checklist

- [ ] One topic only, no unrelated reformatting
- [ ] New or changed behaviour has a test
- [ ] English comments and docstrings, no em dash
- [ ] Existing JSON keys unchanged; new keys documented in `README.md`
- [ ] `experiments/` files state their result in the header
- [ ] I read my own diff before opening this PR
- [ ] If AI wrote part of this, I ran it and understand every line

## Notes for the reviewer

<!-- Anything risky: packet formats, polling, timing, or a trap you hit. -->
