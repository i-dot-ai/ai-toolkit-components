-include ../.env
export

BUILD_TARGETS = mcp_server data_ingestor

build_artifacts/ci:
	mkdir -p -- ../build ../out ../build/layers ../build/packages
	$(foreach target,$(BUILD_TARGETS),$(MAKE) build/callable build_target=$(target);)

build_artifacts/local:
	docker run --rm -v "${PWD}/..:/var/task" -w /var/task --platform linux/amd64 python:3.12 \
		sh -c "pip install uv && make -C terraform build_artifacts/ci"

build/callable:
	cd ../components/${build_target} && $(MAKE) build

TF_BACKEND_CONFIG = backend.hcl
tf_build_args = -var-file="variables/global.tfvars" -var-file="variables/$(env).tfvars"

tf_init:
	terraform init \
		-backend-config=$(TF_BACKEND_CONFIG) \
		-backend-config="dynamodb_table=i-dot-ai-$(env)-dynamo-lock" \
		-reconfigure

tf_plan:
	$(MAKE) tf_init && \
	terraform workspace select $(env) && \
	terraform plan $(tf_build_args) $(args)

tf_apply:
	$(MAKE) tf_init && \
	terraform workspace select $(env) && \
	terraform apply $(tf_build_args) $(args)
