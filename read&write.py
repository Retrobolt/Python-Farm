with open ('file.txt', 'w') as file: # w overwrites the file
    file.write('Hello, world!')

with open ('file.txt', 'r') as file: # reading, w writing, a appending
    text = file.read()
    print(text)

# \n is a new line character, it creates a new line in the text file
# \t is a tab character, it creates a tab in the text file
# \r is a carriage return character, it moves the cursor to the beginning of the line in the text file
# \b is a backspace character, it deletes the previous character in the text file
# \f is a form feed character, it creates a new page in the text file
# These are ASCII control characters, they are used to control the formatting of the text in the text file
