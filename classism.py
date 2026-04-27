class Person:
    def __init__(self, name, age, size):
        self.name = name
        self.age = age
        self.size = size

student = Person("Brandon", 25, "6'1") # Interesting AI Asumptions 4/25/26

print(student) # this will print the memory address of the student object, which is not very useful
print(vars(student)) # vars() is a built-in function that returns the __dict__ attribute of an object, which is a dictionary containing all the attributes of the object and their values. In this case, it will print {'name': 'Brandon', 'age': 25, 'size': "6'1"}
print(student.name) # this will print the name attribute of the student object, which is "Brandon"
print(student.age) # this will print the age attribute of the student object, which is 25
print(student.size) # this will print the size attribute of the student object, which is "6'1"

