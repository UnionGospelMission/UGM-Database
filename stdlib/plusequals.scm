(defmacro (+= var n) (set! ,var (+ ,var ,n)))