CMD =
GH_REPO_OWNER = chmouel
GH_REPO_NAME = scratchmyback
GH_PR_NUM = 345
PASS_TOKEN = github/chmouel-token
PRURL = https://github.com/$(GH_REPO_OWNER)/$(GH_REPO_NAME)/pull/$(GH_PR_NUM)

generate:
	python3 ./tekton-task-embed-script.py base.yaml | prettier --parser=yaml > prow.yaml

sync: generate
	cp -v prow.yaml $$GOPATH/src/github.com/openshift-pipelines/pac/main/.tekton/prow.yaml

test:
	@ [[ -n "$(CMD)" ]] || (echo "Please specify a command to run as argument: like make test CMD=/lgtm" && exit 1)
	@env GH_PR_NUM=$(GH_PR_NUM) GH_REPO_NAME=$(GH_REPO_NAME) GH_REPO_OWNER=$(GH_REPO_OWNER) \
		PAC_TRIGGER_COMMENT="$(CMD)" GITHUB_TOKEN=`pass show $(PASS_TOKEN)` \
		./prow.py

open_pr:
	@if type -p xdg-open; then xdg-open $(PRURL); elif type -p open ;then open $(PRURL);fi

check:
	@make generate && \
		if ! git status prow.yaml|grep -q 'nothing to commit'; then \
			echo 'you need to use make generate';  \
			git diff prow.yaml;  \
			exit 1 ; \
		fi
