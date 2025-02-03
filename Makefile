COMMAND =

generate:
	python3 ./tekton-task-embed-script.py pipelinerun-base.yaml | prettier --parser=yaml > prow.yaml



sync: generate
	cp -v prow.yaml $$GOPATH/src/github.com/openshift-pipelines/pac/main/.tekton/prow.yaml

test:
	@ [[ -n "$(COMMAND)" ]] || (echo "Please specify a command to run as argument: like make test COMMAND=/lgtm" && exit 1)
	@env GH_PR_NUM=345 GH_REPO_NAME=scratchmyback GH_REPO_OWNER=chmouel \
		PAC_TRIGGER_COMMENT="/lgtm" GITHUB_TOKEN=`pass show github/chmouel-token` \
		./prow.py
