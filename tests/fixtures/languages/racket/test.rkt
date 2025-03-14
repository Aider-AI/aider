#lang racket

;; Define a simple greeting function
(define (greet name)
  (string-append "Hello, " name "!"))

;; Example usage
(greet "World")
