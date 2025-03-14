;;; Simple Common Lisp example

(defun greet (name)
  "Return a greeting string for NAME."
  (format nil "Hello, ~a!" name))

(defvar *greeting-style* 'formal
  "Style to use for greetings.")

(defclass person ()
  ((name :initarg :name :accessor person-name)
   (age :initarg :age :accessor person-age))
  (:documentation "A class representing a person."))

(defmethod print-object ((obj person) stream)
  (print-unreadable-object (obj stream :type t)
    (format stream "~a, age ~a" (person-name obj) (person-age obj))))
