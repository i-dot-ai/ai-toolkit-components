TOOL_NAME = mcp_server
BUILD_DIR = ../../build/$(TOOL_NAME)
PACKAGES_DIR = ../../build/packages/$(TOOL_NAME)

.PHONY: build
build:
	rm -rf $(BUILD_DIR) $(PACKAGES_DIR) src/package
	mkdir -p $(BUILD_DIR) $(PACKAGES_DIR)/python

	# Install dependencies into a package directory for the Lambda layer
	docker run --rm -v "$(PWD):/var/task" -w /var/task --platform linux/amd64 python:3.12 \
		sh -c "pip install uv && uv pip install -r src/requirements.txt --target src/package"

	# Copy source files to the build directory
	cp src/main.py $(BUILD_DIR)/
	cp src/server.py $(BUILD_DIR)/
	cp -r src/backends $(BUILD_DIR)/backends
	cp -r src/tools $(BUILD_DIR)/tools

	# Copy packages into the layer
	cp -r src/package/* $(PACKAGES_DIR)/python/
