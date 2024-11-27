(defvar *default-greeting* "Hello")
(defvar *max-name-length* 50)

(defstruct person
  (name "Anonymous")
  (age 0))

(defclass greeter ()
  ((prefix :initarg :prefix
           :accessor greeter-prefix
           :initform *default-greeting*)))

(defmethod greet ((g greeter) (p person))
  (format nil "~A, ~A! You are ~D years old."
          (greeter-prefix g)
          (person-name p)
          (person-age p)))

(defun create-formal-greeter ()
  (make-instance 'greeter :prefix "Good day"))

(defun main ()
  (let ((greeter (create-formal-greeter))
        (person (make-person :name "World" :age 42)))
    (message "%s" (greet greeter person))))
