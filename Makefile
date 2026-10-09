# provingLangSec -- main entry points. Run inside the DevContainer (see README.md).
#   make setup          build the SQLite oracle used by the fidelity harness (needs network once)
#   make demo           the whole demonstration, offline and deterministic (no LLM)
#   make verify         the gate on the verified example
#   make fidelity       does SQLite read our emitted SQL the way the model says?
#   make test           fast unit tests
#   make mutation-test  the gate must reject 14 kinds of broken or cheating submissions
#   make agent          let Claude Code (re)write the example's implementation; the gate decides
#   make approve        owner only: review and approve the frozen files
PY ?= python3 -I
GATE = $(PY) tools/gate/gate.py
PROJECT ?= examples/userdir/gate.toml

.PHONY: setup demo verify fidelity test mutation-test agent agent-selftest approve status clean
setup:
	sh tools/fidelity/build_oracle.sh

test:
	$(PY) tools/gate/test_gate.py

verify:
	$(GATE) check $(PROJECT) $(GATE_FLAGS)

fidelity:
	@test -x build/fidelity/oracle || sh tools/fidelity/build_oracle.sh
	@test -d build/verified/app-py || $(GATE) check $(PROJECT) $(GATE_FLAGS) --skip-tests >/dev/null
	$(PY) tools/fidelity/check_fidelity.py

demo:
	$(PY) tools/demo.py

mutation-test:
	$(PY) tools/gate/mutation_test.py

agent:
	$(PY) tools/agent/run_agent.py $(AGENT_FLAGS)

agent-selftest:
	FAKE_CLAUDE_REFERENCE=$(CURDIR)/examples/userdir/src/App.dfy FAKE_CLAUDE_MODE=solve $(PY) tools/agent/run_agent.py --claude-bin $(CURDIR)/tools/agent/fake_claude.py --attempts 3 --allow-proposed

approve:
	$(PY) tools/gate/approve.py approve

status:
	$(PY) tools/gate/approve.py status

clean:
	rm -rf build runs .gate-state
