variable "source_name" {
  type        = string
  description = "Directory name under components/, e.g. mcp_server"
}

variable "function_name" {
  type        = string
  description = "Name of the Lambda function"
}

variable "runtime" {
  type        = string
  description = "Lambda runtime"
  default     = "python3.12"
}

variable "handler" {
  type        = string
  description = "Lambda handler entrypoint"
  default     = "main.lambda_handler"
}

variable "timeout" {
  type        = number
  description = "Lambda timeout in seconds"
  default     = 60
}

variable "memory_size" {
  type        = number
  description = "Lambda memory in MB"
  default     = 256
}

variable "environment_variables" {
  type        = map(string)
  description = "Environment variables to pass to the Lambda"
  default     = {}
}
