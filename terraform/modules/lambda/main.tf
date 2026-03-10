data "archive_file" "code" {
  type        = "zip"
  source_dir  = "${path.module}/../../../build/${var.source_name}"
  output_path = "${path.module}/../../../out/${var.source_name}.zip"
}

data "archive_file" "layer" {
  type        = "zip"
  source_dir  = "${path.module}/../../../build/packages/${var.source_name}"
  output_path = "${path.module}/../../../build/layers/${var.source_name}.zip"
}

resource "aws_lambda_layer_version" "dependencies" {
  filename         = data.archive_file.layer.output_path
  layer_name       = "${var.function_name}-layer"
  description      = "Dependencies for ${var.function_name}"
  source_code_hash = data.archive_file.layer.output_base64sha256

  compatible_runtimes      = [var.runtime]
  compatible_architectures = ["x86_64"]
}

resource "aws_iam_role" "lambda" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  role             = aws_iam_role.lambda.arn
  runtime          = var.runtime
  handler          = var.handler
  filename         = data.archive_file.code.output_path
  source_code_hash = data.archive_file.code.output_base64sha256
  timeout          = var.timeout
  memory_size      = var.memory_size
  layers           = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = var.environment_variables
  }
}
