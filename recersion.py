def num(value):
    if value <= 0:
        print("Clear")
    else:
        print(value)
        num(value -  1)

num(10)