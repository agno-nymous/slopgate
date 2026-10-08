RUNNER_DIR ?= $(HOME)/actions-runner
RUNNER_LOGS = $(wildcard $(HOME)/Library/Logs/actions.runner.agno-nymous-slopgate.*)

.PHONY: runner-start runner-stop runner-status runner-logs

# svc.sh runs run.sh in the background as a launchd agent. Starting run.sh a second time would conflict with it.
runner-start:
	cd $(RUNNER_DIR) && ./svc.sh start

runner-stop:
	cd $(RUNNER_DIR) && ./svc.sh stop

runner-status:
	cd $(RUNNER_DIR) && ./svc.sh status

runner-logs:
	tail -f $(RUNNER_LOGS)/stdout.log
