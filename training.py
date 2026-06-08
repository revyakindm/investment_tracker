a = " print(1)  \n   print(2)  "
print([x.strip(' ') for x in a.split('\n')])