x = 0

while x <= 5:
    print(x)
    if x == 5:
        print("x is equal to 5")
        # print line break
        print()
    x += 1


TAs = ["Brandon", "Dylan", "Justin", "Kelsey", "Maggie"]
for ta in TAs:
    print(ta)

teen = 12
adult = 18
retired = 65

while True:
    age = input("What is your age? ")
    age = int(age)

    if age < teen:
        print("You are a kid.")
    elif age > teen and age < adult:
        print("You are a teenager.")
    elif age > adult and age < retired:
        print("You are an adult.")
    else:
        print("You are retired.")