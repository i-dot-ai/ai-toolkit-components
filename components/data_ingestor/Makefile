TOOL_NAME = data_ingestor
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
	cp src/ingestor.py $(BUILD_DIR)/
	cp -r src/parsers $(BUILD_DIR)/parsers
	cp -r src/embedders $(BUILD_DIR)/embedders

	# Copy packages into the layer
	cp -r src/package/* $(PACKAGES_DIR)/python/
