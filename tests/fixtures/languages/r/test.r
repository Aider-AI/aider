# Simple R function for testing repository mapping
calculate <- function(x, y) {
  # This function performs a simple calculation
  result <- x * y
  return(result)
}

# Another function to test detection
process_data <- function(data) {
  # Process some data
  return(data * 2)
}

# Example usage
sample_data <- c(1, 2, 3, 4, 5)
result <- calculate(10, 5)
processed <- process_data(sample_data)
