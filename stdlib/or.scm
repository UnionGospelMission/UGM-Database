(define-macro or (lambda args
        (if (null? args) #f
            (if (= (length args) 1) (car args)
                `(if ,(car args) ,(car args) (or ,@(cdr args)) )))))
